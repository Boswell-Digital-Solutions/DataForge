"""Default-deny network guard (layer 2 of docs/proposals/M1_TEST_ISOLATION_REPAIR_DESIGN.md).

This module is not the enforcement. The namespaces are. It makes a blocked attempt
visible, and it covers what the namespaces cannot: a Unix-socket path, an abstract
address, a name lookup and a PostgreSQL target.

It imports only the standard library, and it must not import any network or app module.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import traceback
import weakref

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})
PROXY_VARIABLES = (
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "FTP_PROXY",
    "http_proxy", "https_proxy", "all_proxy", "no_proxy", "ftp_proxy",
)
# Modules that must not be loaded before the guard (checked by the pytest plugin).
WATCHED_MODULES = (
    "pytest", "_pytest", "httpx", "requests", "urllib3", "redis",
    "psycopg2", "psycopg", "sqlalchemy", "app",
)
ALLOWED_FAMILIES = (1, 2, 10)  # AF_UNIX, AF_INET, AF_INET6
EXIT_VIOLATION = 87

INSTALLED = False
RUN_ID = None
MANIFEST: dict = {}
EARLY_IMPORTS: list = []
CURRENT_TEST = None
VIOLATION_COUNT = 0

_local = threading.local()
_bound_sockets: "weakref.WeakSet" = weakref.WeakSet()
_violations_fd = None
_absent_fd = None


class NetworkIsolationViolation(BaseException):
    """A blocked attempt. It is a BaseException so that `except Exception` cannot swallow it."""


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------

def _fatal(message: str) -> None:
    try:
        os.write(2, ("NETGUARD-FATAL " + message + "\n").encode())
    finally:
        os._exit(EXIT_VIOLATION)


def _short_stack() -> list:
    frames = traceback.extract_stack(limit=14)[:-3]
    return ["%s:%d %s" % (os.path.basename(f.filename), f.lineno, f.name) for f in frames[-6:]]


def _append(fd, record: dict) -> None:
    data = (json.dumps(record, sort_keys=True) + "\n").encode()
    if os.write(fd, data) != len(data):
        raise OSError("short write")


def _record(kind: str, target) -> dict:
    return {
        "ts": round(time.time(), 3),
        "pid": os.getpid(),
        "kind": kind,
        "target": repr(target)[:300],
        "test": CURRENT_TEST or os.environ.get("NETGUARD_CURRENT_TEST", ""),
        "stack": _short_stack(),
    }


def violate(kind: str, target) -> None:
    """Record a violation and raise. If the record cannot be written, stop the process."""
    global VIOLATION_COUNT
    record = _record(kind, target)
    try:
        _append(_violations_fd, record)
    except Exception as exc:  # noqa: BLE001 - any failure to record is fatal
        _fatal("cannot write violations.jsonl: %r" % (exc,))
    VIOLATION_COUNT += 1
    # A second channel that the runner reads from the output stream.
    try:
        os.write(2, ("NETGUARD-VIOLATION " + json.dumps(record, sort_keys=True) + "\n").encode())
    except OSError:
        pass
    raise NetworkIsolationViolation("%s: %s" % (kind, record["target"]))


def note_declared_absent(service: str, target) -> None:
    record = _record("declared-absent probe", target)
    record["service"] = service
    try:
        _append(_absent_fd, record)
    except Exception as exc:  # noqa: BLE001
        _fatal("cannot write declared-absent log: %r" % (exc,))


# ---------------------------------------------------------------------------
# Allow-list decisions
# ---------------------------------------------------------------------------

def _tcp_allowed(host: str, port: int) -> bool:
    for entry in MANIFEST.get("tcp", ()):
        if entry["host"] == host and entry["port"] == port:
            return True
    return False


def _is_loopback(host) -> bool:
    return isinstance(host, str) and host in LOOPBACK_HOSTS


def _port_bound_here(port: int) -> bool:
    for sock in list(_bound_sockets):
        try:
            if sock.fileno() != -1 and sock.getsockname()[1] == port:
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


def check_unix_path(path, kind: str) -> None:
    if isinstance(path, bytes):
        if path[:1] == b"\0" or not path:
            violate(kind + ": abstract or empty AF_UNIX address", path)
        path = os.fsdecode(path)
    if not isinstance(path, str) or not path or path[0] == "\0":
        violate(kind + ": abstract or empty AF_UNIX address", path)
    real = os.path.realpath(path)
    for entry in MANIFEST.get("unix", ()):
        if real == os.path.realpath(entry["path"]):
            return
    for entry in MANIFEST.get("declared_absent", ()):
        if real == os.path.realpath(entry["path"]):
            note_declared_absent(entry["service"], path)
            return
    violate(kind + ": AF_UNIX path not in the manifest", real)


def check_inet(address, kind: str, bind: bool = False) -> None:
    if not isinstance(address, tuple) or len(address) < 2:
        violate(kind + ": unusable address", address)
    host, port = address[0], address[1]
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    if not _is_loopback(host):
        violate(kind + ": host is not loopback", address)
    if bind:
        return
    if _tcp_allowed("127.0.0.1", port):
        return
    if _port_bound_here(port):
        return
    violate(kind + ": loopback port not in the manifest", address)


def check_address(sock, address, kind: str, bind: bool = False) -> None:
    family = getattr(sock, "family", None)
    family = int(family) if family is not None else None
    if family == 1:
        check_unix_path(address, kind)
    elif family in (2, 10):
        check_inet(address, kind, bind=bind)
    else:
        violate(kind + ": socket family not allowed", family)


# ---------------------------------------------------------------------------
# Audit hook
# ---------------------------------------------------------------------------

def _name_of(value):
    if isinstance(value, tuple) and value:
        value = value[0]
    return value


def _check_name(value, kind: str) -> None:
    value = _name_of(value)
    if value is None or value == "":
        return
    if isinstance(value, bytes):
        value = value.decode("ascii", "replace")
    if not _is_loopback(value):
        violate(kind + ": name lookup not allowed", value)


def _program_allowed(name: str) -> bool:
    base = os.path.basename(str(name))
    for allowed in MANIFEST.get("programs", ()):
        if base == allowed or (allowed.endswith("*") and base.startswith(allowed[:-1])):
            return True
    return False


def _hook(event: str, args: tuple) -> None:
    if getattr(_local, "busy", False):
        return
    if not event.startswith(("socket.", "subprocess.", "os.system", "os.exec", "os.posix_spawn", "os.spawn")):
        return
    _local.busy = True
    try:
        if event == "socket.connect":
            check_address(args[0], args[1], event)
        elif event in ("socket.sendto", "socket.sendmsg"):
            check_address(args[0], args[1], event)
        elif event == "socket.bind":
            check_address(args[0], args[1], event, bind=True)
            try:
                _bound_sockets.add(args[0])
            except TypeError:
                pass
        elif event == "socket.__new__":
            family = int(args[1])
            if family != -1 and family not in ALLOWED_FAMILIES:
                violate(event + ": socket family not allowed", family)
        elif event == "socket.getaddrinfo":
            _check_name(args[0], event)
        elif event in ("socket.gethostbyname", "socket.gethostbyaddr"):
            _check_name(args[0], event)
        elif event == "socket.getnameinfo":
            _check_name(args[0], event)
        elif event == "subprocess.Popen":
            exe = args[0] or (args[1][0] if args[1] else "")
            if not _program_allowed(exe):
                violate("spawn of a program that is not in the manifest", exe)
        elif event in ("os.exec", "os.posix_spawn", "os.spawn"):
            if not _program_allowed(args[0]):
                violate("spawn of a program that is not in the manifest", args[0])
        elif event == "os.system":
            violate("os.system is not allowed", args[0])
    finally:
        _local.busy = False


# ---------------------------------------------------------------------------
# PostgreSQL wrappers (libpq opens its own sockets, so the audit hook cannot see them)
# ---------------------------------------------------------------------------

def check_pg_target(dsn=None, **kwargs) -> None:
    params: dict = {}
    if dsn:
        try:
            import psycopg2.extensions as ext  # already imported by the caller

            params.update(ext.parse_dsn(dsn))
        except Exception:  # noqa: BLE001
            violate("psycopg: unparsable DSN", "<dsn>")
    params.update({k: v for k, v in kwargs.items() if v not in (None, "")})
    for key in ("service", "passfile", "sslrootcert"):
        if key == "service" and params.get(key):
            violate("psycopg: libpq service file is not allowed", params[key])
    hosts = str(params.get("host") or "")
    ports = str(params.get("port") or "5432")
    if not hosts:
        violate("psycopg: empty host means the default socket", "")
    host_list = hosts.split(",")
    port_list = ports.split(",")
    for index, host in enumerate(host_list):
        port = port_list[index] if index < len(port_list) else port_list[-1]
        if host.startswith("/"):
            check_unix_path(os.path.join(host, ".s.PGSQL." + port), "psycopg")
        elif _is_loopback(host) and port.isdigit() and _tcp_allowed("127.0.0.1", int(port)):
            continue
        else:
            violate("psycopg: host and port are not in the manifest", (host, port))
    hostaddr = str(params.get("hostaddr") or "")
    if hostaddr:
        violate("psycopg: hostaddr is not allowed", hostaddr)


def _patch_psycopg2(module) -> None:
    original = module.connect

    def connect(dsn=None, *args, **kwargs):
        _local.busy = True
        try:
            check_pg_target(dsn, **kwargs)
        finally:
            _local.busy = False
        return original(dsn, *args, **kwargs)

    connect.__wrapped__ = original
    module.connect = connect


def _patch_psycopg(module) -> None:
    connection = getattr(module, "Connection", None)
    if connection is None:
        return
    original = connection.connect.__func__

    def connect(cls, conninfo="", *args, **kwargs):
        try:
            from psycopg.conninfo import conninfo_to_dict

            params = conninfo_to_dict(conninfo, **kwargs)
        except Exception:  # noqa: BLE001
            violate("psycopg: unparsable conninfo", "<conninfo>")
        _local.busy = True
        try:
            check_pg_target(None, **params)
        finally:
            _local.busy = False
        return original(cls, conninfo, *args, **kwargs)

    connection.connect = classmethod(connect)


_POST_IMPORT = {"psycopg2": _patch_psycopg2, "psycopg": _patch_psycopg}


class _PostImportFinder:
    """Patch psycopg2 and psycopg right after their first import."""

    def find_spec(self, name, path=None, target=None):
        if name not in _POST_IMPORT or getattr(_local, "finding", False):
            return None
        import importlib.util

        _local.finding = True
        try:
            spec = importlib.util.find_spec(name)
        finally:
            _local.finding = False
        if spec is None or spec.loader is None:
            return None
        loader = spec.loader
        original_exec = loader.exec_module

        def exec_module(module, _orig=original_exec, _name=name):
            _orig(module)
            _POST_IMPORT[_name](module)

        loader.exec_module = exec_module
        return spec


# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------

def install() -> None:
    """Install the guard. It does nothing unless the runner set NETGUARD_RUN_ID."""
    global INSTALLED, RUN_ID, MANIFEST, EARLY_IMPORTS, _violations_fd, _absent_fd
    if INSTALLED:
        return
    run_id = os.environ.get("NETGUARD_RUN_ID")
    manifest_path = os.environ.get("NETGUARD_MANIFEST")
    if not run_id or not manifest_path:
        return
    EARLY_IMPORTS = sorted(m for m in WATCHED_MODULES if m in sys.modules)
    try:
        with open(manifest_path, "r", encoding="utf-8") as handle:
            MANIFEST = json.load(handle)
        if MANIFEST.get("run_id") != run_id:
            _fatal("manifest run_id does not match NETGUARD_RUN_ID")
        for entry in MANIFEST.get("tcp", ()):
            if entry.get("host") != "127.0.0.1":
                _fatal("manifest entry %r is not a loopback service" % (entry,))
        for entry in [*MANIFEST.get("unix", ()), *MANIFEST.get("declared_absent", ())]:
            if not os.path.isabs(entry.get("path", "")):
                _fatal("manifest entry %r has no absolute path" % (entry,))
        _violations_fd = os.open(MANIFEST["violations_path"], os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        _absent_fd = os.open(MANIFEST["declared_absent_log"], os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    except Exception as exc:  # noqa: BLE001
        _fatal("cannot load the manifest or open the records: %r" % (exc,))
    RUN_ID = run_id
    bad = inherited_fd_problems()
    if bad:
        _fatal("inherited descriptors that are not a file, a pipe or /dev/null: %s" % "; ".join(bad))
    for name in PROXY_VARIABLES:
        if os.environ.get(name):
            INSTALLED = True
            violate("a proxy variable is set", name)
    sys.addaudithook(_hook)
    sys.meta_path.insert(0, _PostImportFinder())
    INSTALLED = True
    try:
        snapshot = os.path.join(MANIFEST["log_dir"], "snapshot-%d.json" % os.getpid())
        with open(snapshot, "w", encoding="utf-8") as handle:
            json.dump({"pid": os.getpid(), "early_imports": EARLY_IMPORTS, "inherited_fd_problems": [], "argv": sys.argv[:3]}, handle)
    except OSError:
        pass


def inherited_fd_problems() -> list:
    """Descriptors that the process holds at start and that are not a regular file, a pipe or /dev/null.

    A connected socket on fd 0 to 2 or above would bypass the namespaces.
    """
    import stat

    problems = []
    null = os.stat("/dev/null")
    try:
        names = os.listdir("/proc/self/fd")
    except OSError:
        return ["cannot list /proc/self/fd"]
    for name in names:
        fd = int(name)
        try:
            st = os.fstat(fd)
        except OSError:
            continue  # the descriptor of listdir itself
        if stat.S_ISREG(st.st_mode) or stat.S_ISFIFO(st.st_mode):
            continue
        if stat.S_ISCHR(st.st_mode) and st.st_rdev == null.st_rdev:
            continue
        if stat.S_ISCHR(st.st_mode) and fd <= 2:
            continue  # a terminal on a standard stream, never a socket
        try:
            target = os.readlink("/proc/self/fd/" + name)
        except OSError:
            target = "?"
        problems.append("fd %d: %s" % (fd, target))
    return problems


def violation_lines() -> int:
    """Count the lines of the violation record (children included)."""
    if not MANIFEST:
        return 0
    try:
        with open(MANIFEST["violations_path"], "rb") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return -1
