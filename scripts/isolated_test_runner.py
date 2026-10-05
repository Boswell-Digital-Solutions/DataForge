#!/usr/bin/env python3
"""Isolated test runner for DataForge (finding M1).

Design: docs/proposals/M1_TEST_ISOLATION_REPAIR_DESIGN.md (revision 5). Layer 1 is the
enforcement: a user, network, pid and mount namespace with an empty root. The runner
never falls back to an unguarded run. If it cannot isolate, it exits 86.

Exit codes: 86 precondition, 87 violation or refused run, 88 teardown, else the pytest status.

Usage:  scripts/run-tests-isolated.sh [options] [-- PYTEST_ARGS...]

This file also holds the in-sandbox launcher (`--internal-stage1` and `--internal-stage2`).
The launcher runs without the guard. It must not import any application module.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import platform
import pwd
import random
import re
import secrets
import shutil
import signal
import socket
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path

EXIT_PRECONDITION = 86
EXIT_VIOLATION = 87
EXIT_TEARDOWN = 88

REPO = Path(__file__).resolve().parents[1]
ISOLATION_DIR = REPO / "tests" / "isolation"
GUARD_FILES = ("netguard.py", "sitecustomize.py", "pytest_plugin.py", "stub_neuroforge.py")
RUN_PARENT = "/tmp"
SANDBOX_USER = "dftest"
PROXY_VARIABLES = (
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "FTP_PROXY",
    "http_proxy", "https_proxy", "all_proxy", "no_proxy", "ftp_proxy",
)
WRITABLE_REPO_DIRS = ("htmlcov", "logs", "reports")
WRITABLE_REPO_FILES = ("coverage.xml",)
REDIS_ABSENT_REASON = "the decision owner declared Redis absent; no disposable Redis image is cached locally"
DEFAULT_PREFLIGHT_MODULES = "ssl,sqlite3,json,pytest,psycopg2"
# Trees that must never be bound into the sandbox (they hold the sockets of section 3, item 9).
FORBIDDEN_TREES = ("/", "/var", "/run", "/var/run", "/home", "/root", "/tmp", "/dev", "/proc", "/sys", "/etc")

# ---------------------------------------------------------------------------
# Seccomp filter (x86_64 only). A pinned generator. The digest is checked at start.
# ---------------------------------------------------------------------------

SECCOMP_ARCH = "x86_64"
AUDIT_ARCH_X86_64 = 0xC000003E
X32_BIT = 0x40000000
SYS_SOCKET = 41
SYS_IO_URING = (425, 426, 427)  # io_uring_setup, io_uring_enter, io_uring_register
ALLOWED_FAMILIES = (1, 2, 10)  # AF_UNIX, AF_INET, AF_INET6
RET_ALLOW = 0x7FFF0000
RET_KILL_PROCESS = 0x80000000
RET_ERRNO = 0x00050000
EPERM, EAFNOSUPPORT = 1, 97
# The digest of the bytes that build_seccomp_x86_64() returns. Change it only with the generator.
PINNED_SECCOMP_SHA256 = "64da29b37c71f460e65a99fda51e67c5ce69e22c2ebe2c467b697ece88f9cfe6"


def build_seccomp_x86_64() -> bytes:
    """Build a classic BPF program: the architecture check, an x32 deny, a socket family
    allow-list (AF_UNIX, AF_INET, AF_INET6) and a deny of io_uring_setup/enter/register."""
    ops = []  # (code, jt_label, jf_label, k) or ("label", name)

    def ins(code, k, jt=None, jf=None):
        ops.append((code, jt, jf, k))

    def label(name):
        ops.append(("label", name))

    LD_ABS, JEQ, JSET, RET = 0x20, 0x15, 0x45, 0x06
    ins(LD_ABS, 4)                                     # seccomp_data.arch
    ins(JEQ, AUDIT_ARCH_X86_64, jt="ok_arch", jf="kill")
    label("ok_arch")
    ins(LD_ABS, 0)                                     # seccomp_data.nr
    ins(JSET, X32_BIT, jt="eperm", jf="nr")            # the x32 ABI has bit 30 set
    label("nr")
    ins(JEQ, SYS_SOCKET, jt="sock", jf="n1")
    label("n1")
    ins(JEQ, SYS_IO_URING[0], jt="eperm", jf="n2")
    label("n2")
    ins(JEQ, SYS_IO_URING[1], jt="eperm", jf="n3")
    label("n3")
    ins(JEQ, SYS_IO_URING[2], jt="eperm", jf="allow")
    label("sock")
    ins(LD_ABS, 16)                                    # seccomp_data.args[0], low word (int family)
    ins(JEQ, ALLOWED_FAMILIES[0], jt="allow", jf="f1")
    label("f1")
    ins(JEQ, ALLOWED_FAMILIES[1], jt="allow", jf="f2")
    label("f2")
    ins(JEQ, ALLOWED_FAMILIES[2], jt="allow", jf="eafnosupport")
    label("eafnosupport")
    ins(RET, RET_ERRNO | EAFNOSUPPORT)
    label("eperm")
    ins(RET, RET_ERRNO | EPERM)
    label("kill")
    ins(RET, RET_KILL_PROCESS)
    label("allow")
    ins(RET, RET_ALLOW)

    positions, index = {}, 0
    for op in ops:
        if op[0] == "label":
            positions[op[1]] = index
        else:
            index += 1
    out, index = bytearray(), 0
    for op in ops:
        if op[0] == "label":
            continue
        code, jt, jf, k = op
        jt_off = 0 if jt is None else positions[jt] - index - 1
        jf_off = 0 if jf is None else positions[jf] - index - 1
        if jt_off < 0 or jf_off < 0 or jt_off > 255 or jf_off > 255:
            raise ValueError("bad jump in the seccomp program")
        out += struct.pack("<HBBI", code, jt_off, jf_off, k)
        index += 1
    return bytes(out)


def seccomp_digest() -> str:
    return hashlib.sha256(build_seccomp_x86_64()).hexdigest()


def install_seccomp(program: bytes) -> None:
    """Install the filter with prctl. It needs NoNewPrivs, which is already set."""
    libc = ctypes.CDLL(None, use_errno=True)

    class SockFprog(ctypes.Structure):
        _fields_ = [("len", ctypes.c_ushort), ("filter", ctypes.c_void_p)]

    buf = ctypes.create_string_buffer(program, len(program))
    fprog = SockFprog(len(program) // 8, ctypes.cast(buf, ctypes.c_void_p))
    if libc.prctl(38, 1, 0, 0, 0) != 0:  # PR_SET_NO_NEW_PRIVS
        raise OSError(ctypes.get_errno(), "prctl NO_NEW_PRIVS")
    if libc.prctl(22, 2, ctypes.byref(fprog), 0, 0) != 0:  # PR_SET_SECCOMP, SECCOMP_MODE_FILTER
        raise OSError(ctypes.get_errno(), "prctl SECCOMP")


# ---------------------------------------------------------------------------
# Small pure helpers (the canaries test them)
# ---------------------------------------------------------------------------

class Precondition(Exception):
    """A precondition of the runner failed. The runner exits 86."""


def proxy_variables_set(env) -> list:
    return [name for name in PROXY_VARIABLES if env.get(name)]


def find_dotenv_files(start: Path) -> list:
    """Return every .env file in `start` and its parents (load_dotenv walks up)."""
    found = []
    current = Path(start).resolve()
    for directory in [current, *current.parents]:
        candidate = directory / ".env"
        if candidate.exists():
            found.append(str(candidate))
    return found


def ephemeral_range() -> tuple:
    try:
        low, high = Path("/proc/sys/net/ipv4/ip_local_port_range").read_text().split()
        return int(low), int(high)
    except (OSError, ValueError):
        return 32768, 60999


def choose_stub_port(requested: "int | None" = None) -> int:
    low, high = ephemeral_range()
    if requested is not None:
        if low <= requested <= high or not 1024 <= requested <= 65535:
            raise Precondition("the stub port %d is in the ephemeral range %d-%d or invalid" % (requested, low, high))
        return requested
    while True:
        port = random.SystemRandom().randint(20000, 29999)
        if not low <= port <= high:
            return port


def parse_proc_status(text: str) -> dict:
    values = {}
    for line in text.splitlines():
        key, _, rest = line.partition(":")
        values[key.strip()] = rest.strip()
    return values


def read_proc_status() -> dict:
    return parse_proc_status(Path("/proc/self/status").read_text())


def is_forbidden_tree(path: str) -> bool:
    real = os.path.realpath(path)
    return real in FORBIDDEN_TREES


def interpreter_trees() -> list:
    """Trees to bind read only so that the interpreter, its library and its venv exist."""
    candidates = {
        os.path.realpath(sys.prefix), os.path.realpath(sys.base_prefix), os.path.realpath(sys.exec_prefix),
        os.path.dirname(os.path.dirname(os.path.realpath(sys.executable))),
    }
    for entry in sys.path:
        if entry and os.path.isdir(entry) and "site-packages" in entry:
            candidates.add(os.path.realpath(entry))
    trees = []
    for path in sorted(candidates, key=len):
        if path == "/usr" or path.startswith("/usr/"):
            continue
        if is_forbidden_tree(path):
            raise Precondition("the interpreter tree %s is too broad to bind" % path)
        if any(path == t or path.startswith(t + "/") for t in trees):
            continue
        trees.append(path)
    return trees


def git_trees(repo: Path) -> list:
    """The git directory of a worktree sits outside the repository. Bind it read only."""
    dot_git = repo / ".git"
    if not dot_git.is_file():
        return []
    text = dot_git.read_text().strip()
    if not text.startswith("gitdir:"):
        return []
    gitdir = Path(text.split(":", 1)[1].strip())
    if not gitdir.is_absolute():
        gitdir = (repo / gitdir).resolve()
    trees = [str(gitdir)]
    common = gitdir / "commondir"
    if common.exists():
        trees = [str((gitdir / common.read_text().strip()).resolve()), str(gitdir)]
    return trees


# ---------------------------------------------------------------------------
# The sandbox plan (the same list builds the bwrap arguments and the plain mounts)
# ---------------------------------------------------------------------------

def build_plan(run_dir: str, repo: Path, with_postgres: bool, etc_dir: str, extra_ro: "list | None" = None,
               omit_interpreter_trees: bool = False) -> list:
    """Return an ordered list of operations. The first entry makes the private /tmp."""
    plan = [("tmpfs", "/tmp")]
    for name in ("bin", "sbin", "lib", "lib32", "lib64", "libx32"):
        path = "/" + name
        if os.path.islink(path):
            plan.append(("symlink", os.readlink(path), path))
        elif os.path.isdir(path):
            plan.append(("bind", path, path, True))
    plan.append(("bind", "/usr", "/usr", True))
    for name in ("hosts", "nsswitch.conf", "passwd", "group"):
        plan.append(("bind", os.path.join(etc_dir, name), "/etc/" + name, True))
    plan.append(("proc", "/proc"))
    plan.append(("dev", "/dev"))
    for tree in [] if omit_interpreter_trees else interpreter_trees():
        plan.append(("bind", tree, tree, True))
    repo_str = str(repo)
    plan.append(("bind", repo_str, repo_str, True))
    for tree in git_trees(repo):
        plan.append(("bind", tree, tree, True))
    for name in WRITABLE_REPO_DIRS:
        if (repo / name).is_dir():
            plan.append(("bind", str(repo / name), str(repo / name), False))
    for name in WRITABLE_REPO_FILES:
        if (repo / name).is_file():
            plan.append(("bind", str(repo / name), str(repo / name), False))
    guard_dir = os.path.join(run_dir, "guard")
    plan.append(("bind", guard_dir, guard_dir, True))
    plan.append(("bind", os.path.join(run_dir, "manifest.json"), os.path.join(run_dir, "manifest.json"), True))
    plan.append(("bind", os.path.join(run_dir, "launch.json"), os.path.join(run_dir, "launch.json"), True))
    # The violation record is bound as a file (a mount point), so the test process cannot unlink or rename it.
    viol_file = os.path.join(run_dir, "viol", "violations.jsonl")
    plan.append(("bind", viol_file, viol_file, False))
    plan.append(("bind", os.path.join(run_dir, "log"), os.path.join(run_dir, "log"), False))
    if with_postgres:
        plan.append(("bind", os.path.join(run_dir, "pg"), os.path.join(run_dir, "pg"), True))
    for tree in extra_ro or []:
        plan.append(("bind", tree, tree, True))
    return plan


def bwrap_args(plan: list, seccomp_fd: int, repo: Path) -> list:
    args = [
        "bwrap", "--unshare-user", "--unshare-net", "--unshare-pid", "--unshare-ipc",
        "--die-with-parent", "--new-session", "--cap-drop", "ALL", "--seccomp", str(seccomp_fd),
    ]
    for op in plan:
        if op[0] == "tmpfs":
            args += ["--tmpfs", op[1]]
        elif op[0] == "symlink":
            args += ["--symlink", op[1], op[2]]
        elif op[0] == "bind":
            args += ["--ro-bind" if op[3] else "--bind", op[1], op[2]]
        elif op[0] == "proc":
            args += ["--proc", op[1]]
        elif op[0] == "dev":
            args += ["--dev", op[1]]
    args += ["--remount-ro", "/", "--chdir", str(repo)]
    return args


# ---------------------------------------------------------------------------
# Plain route: stage 1 (privileged helper, inside `unshare -rnmpf --propagation private`)
# ---------------------------------------------------------------------------

MS_RDONLY, MS_NOSUID, MS_NODEV, MS_NOEXEC = 1, 2, 4, 8
MS_NOATIME, MS_NODIRATIME, MS_REMOUNT, MS_BIND, MS_REC = 1024, 2048, 32, 4096, 16384
MS_RELATIME = 1 << 21
MNT_DETACH = 2
SYS_PIVOT_ROOT = 155
_libc = None


def libc():
    global _libc
    if _libc is None:
        _libc = ctypes.CDLL(None, use_errno=True)
    return _libc


def _mount(source, target, fstype, flags, data=None) -> None:
    result = libc().mount(
        source.encode() if source else None, target.encode(), fstype.encode() if fstype else None,
        ctypes.c_ulong(flags), data.encode() if data else None,
    )
    if result != 0:
        err = ctypes.get_errno()
        raise OSError(err, "mount %s -> %s failed: %s" % (source, target, os.strerror(err)))


def _locked_flags(path: str) -> int:
    """The mount flags that a user namespace cannot clear. A read-only remount must keep them."""
    f = os.statvfs(path).f_flag
    flags = 0
    for st, ms in ((2, MS_NOSUID), (4, MS_NODEV), (8, MS_NOEXEC), (1024, MS_NOATIME), (2048, MS_NODIRATIME), (4096, MS_RELATIME)):
        if f & st:
            flags |= ms
    return flags


def _bind(src: str, dst: str, read_only: bool) -> None:
    if os.path.isdir(src):
        os.makedirs(dst, exist_ok=True)
    else:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.lexists(dst):
            open(dst, "wb").close()
    _mount(src, dst, None, MS_BIND | MS_REC)
    if read_only:
        _mount(None, dst, None, MS_REMOUNT | MS_BIND | MS_RDONLY | _locked_flags(src))


def apply_plan(plan: list, newroot: str) -> None:
    for op in plan:
        kind = op[0]
        if kind == "tmpfs":
            os.makedirs(newroot + op[1], exist_ok=True)
            _mount("tmpfs", newroot + op[1], "tmpfs", MS_NOSUID | MS_NODEV, "mode=1777")
        elif kind == "symlink":
            os.symlink(op[1], newroot + op[2])
        elif kind == "bind":
            _bind(op[1], newroot + op[2], op[3])
        elif kind == "proc":
            os.makedirs(newroot + op[1], exist_ok=True)
            _mount("proc", newroot + op[1], "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC)
        elif kind == "dev":
            dev = newroot + op[1]
            os.makedirs(dev, exist_ok=True)
            _mount("tmpfs", dev, "tmpfs", MS_NOSUID, "mode=755")
            for node in ("null", "zero", "full", "random", "urandom", "tty"):
                if os.path.exists("/dev/" + node):
                    open(dev + "/" + node, "wb").close()
                    _mount("/dev/" + node, dev + "/" + node, None, MS_BIND)
            os.makedirs(dev + "/shm", exist_ok=True)
            _mount("tmpfs", dev + "/shm", "tmpfs", MS_NOSUID | MS_NODEV, "mode=1777")
            for name, target in (("fd", "/proc/self/fd"), ("stdin", "/proc/self/fd/0"),
                                 ("stdout", "/proc/self/fd/1"), ("stderr", "/proc/self/fd/2")):
                os.symlink(target, dev + "/" + name)


def pivot_into(newroot: str) -> None:
    os.makedirs(newroot + "/old", exist_ok=True)
    os.chdir(newroot)
    if libc().syscall(SYS_PIVOT_ROOT, b".", b"old") != 0:
        err = ctypes.get_errno()
        raise OSError(err, "pivot_root failed: %s" % os.strerror(err))
    os.chdir("/")
    if libc().umount2(b"/old", MNT_DETACH) != 0:
        err = ctypes.get_errno()
        raise OSError(err, "umount of the old root failed: %s" % os.strerror(err))
    os.rmdir("/old")


def status_line(config: dict, step: str, ok: bool, detail="") -> None:
    record = {"step": step, "ok": ok, "detail": detail, "pid": os.getpid(), "ts": round(time.time(), 3)}
    with open(os.path.join(config["log_dir"], "status.jsonl"), "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def fail_launcher(config: dict, step: str, detail: str) -> "None":
    try:
        status_line(config, step, False, detail)
    except OSError:
        pass
    sys.stderr.write("NETGUARD-PRECONDITION %s: %s\n" % (step, detail))
    sys.stderr.flush()
    os._exit(EXIT_PRECONDITION)


# THE LAUNCHER SEQUENCE (one numbered list; the comments below use these numbers). The launcher runs
# without the guard. The bwrap route does L1 (it brings loopback up itself), L3 and L4 by its own options.
#   L1  loopback up                        plain route only, stage 1 (needs iproute2)
#   L2  control capability check           plain route only, stage 1, before the drop; it must show privilege
#   L3  mounts: allow-list, /proc, minimal /dev, pivot_root, rmdir /old, read-only root   (plain: stage 1)
#   L4  drop capabilities, set no-new-privs, start stage 2                                (plain: stage 1)
#   L5  preflight inside the final sandbox: interpreter modules and the programs bash, git, openssl
#   L6  loopback self-connect proof
#   L7  capability proof of the final process (CapEff, CapBnd zero, NoNewPrivs 1, uid)
#   L8  seccomp filter (bwrap loaded it; the plain route installs it) and its digest
#   L9  AF_VSOCK canary (creation only, never a connect)
#   L10 synthetic /etc proof, with the filter active
#   L11 inside service: the NeuroForge stub starts (unguarded) and proves its identity
#   L12 PostgreSQL identity from inside (the marker that the runner wrote)
#   L13 optional alembic migration, under the guard
#   L14 start pytest with the guard directory first on PYTHONPATH
#   L15 stop the stub


def stage1(config_path: str) -> int:
    """Plain route, privileged helper: L1 to L4."""
    config = json.loads(Path(config_path).read_text())
    status_line(config, "stage1-start", True, "uid=%d" % os.getuid())
    try:
        # L1. Bring loopback up (the plain route needs it; the bwrap route has it up already).
        ip = subprocess.run(["ip", "link", "set", "lo", "up"], capture_output=True, text=True)
        if ip.returncode != 0:
            fail_launcher(config, "loopback-up", ip.stderr.strip())
        # L2. Control capability check, before the drop. It must show privilege, or the check is broken.
        control = read_proc_status()
        cap_eff = int(control.get("CapEff", "0"), 16)
        status_line(config, "capability-control", cap_eff != 0, "CapEff=%s" % control.get("CapEff"))
        if cap_eff == 0:
            fail_launcher(config, "capability-control", "the control process shows no privilege; the check cannot detect it")
        # L3. Mounts: the allow-list into a tmpfs root, then /proc, minimal /dev, pivot_root, rmdir /old, read-only root.
        newroot = os.path.join(config["run_dir"], "root")
        os.makedirs(newroot, exist_ok=True)
        _mount("tmpfs", newroot, "tmpfs", MS_NOSUID | MS_NODEV, "mode=755")
        apply_plan([tuple(op) for op in config["plan"]], newroot)
        pivot_into(newroot)
        _mount(None, "/", None, MS_REMOUNT | MS_BIND | MS_RDONLY | MS_NOSUID | MS_NODEV)  # the root is read only
        status_line(config, "mounts", True, ",".join(sorted(os.listdir("/"))))
    except OSError as exc:
        fail_launcher(config, "mounts", str(exc))
    # L4. Drop every capability and set no-new-privs, then start stage 2.
    command = [
        "setpriv", "--no-new-privs", "--bounding-set=-all", "--inh-caps=-all",
        config["python"], str(REPO / "scripts" / "isolated_test_runner.py"), "--internal-stage2", config_path,
    ]
    os.chdir(config["repo"])
    return subprocess.run(command, env=config["launcher_env"]).returncode


# ---------------------------------------------------------------------------
# Stage 2 (final process of both routes): proofs, inside services, then pytest
# ---------------------------------------------------------------------------

def loopback_proof() -> str:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    client = socket.create_connection(("127.0.0.1", port), timeout=5)
    conn, _ = server.accept()
    client.sendall(b"x")
    ok = conn.recv(1) == b"x"
    for s in (client, conn, server):
        s.close()
    if not ok:
        raise RuntimeError("no data crossed loopback")
    return "127.0.0.1:%d" % port


def http_get_health(port: int) -> dict:
    import http.client

    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    conn.request("GET", "/health")
    response = conn.getresponse()
    body = response.read()
    conn.close()
    if response.status != 200:
        raise RuntimeError("health answered %d" % response.status)
    return json.loads(body)


def vsock_blocked() -> str:
    """Create a socket of AF_VSOCK (family 40) with a C call. It must fail. It never connects."""
    c = ctypes.CDLL(None, use_errno=True)
    results = []
    for family in (40, 16, 17):  # AF_VSOCK, AF_NETLINK, AF_PACKET
        fd = c.socket(family, 1 if family != 17 else 3, 0)
        err = ctypes.get_errno()
        if fd >= 0:
            os.close(fd)
            raise RuntimeError("a socket of family %d was created" % family)
        results.append("%d:errno%d" % (family, err))
    return ",".join(results)


def stage2(config_path: str) -> int:
    config = json.loads(Path(config_path).read_text())
    route = config["route"]
    status_line(config, "stage2-start", True, "route=%s uid=%d" % (route, os.getuid()))
    # L1 to L4 ran before this process (bwrap options, or stage 1 of the plain route).
    # L5. Preflight inside the final sandbox: inherited descriptors, the interpreter modules and the programs.
    sys.path.insert(0, os.path.join(config["run_dir"], "guard"))
    import netguard  # only for its descriptor check; the guard is not installed in the launcher

    bad_fds = netguard.inherited_fd_problems()
    if bad_fds:
        fail_launcher(config, "preflight-descriptors", "; ".join(bad_fds))
    sys.path.pop(0)
    modules = [m for m in config["preflight_modules"].split(",") if m]
    code = "import " + ", ".join(modules) if modules else "pass"
    pre = subprocess.run([config["python"], "-c", code], capture_output=True, text=True, env=config["launcher_env"])
    if pre.returncode != 0:
        fail_launcher(config, "preflight-interpreter", pre.stderr.strip()[-300:])
    for program in ("bash", "git", "openssl"):
        found = shutil.which(program, path=config["launcher_env"]["PATH"])
        probe = subprocess.run([found or program, "--version" if program != "openssl" else "version"],
                               capture_output=True, text=True) if found else None
        if probe is None or probe.returncode != 0:
            fail_launcher(config, "preflight-programs", "%s is missing in the sandbox" % program)
    status_line(config, "preflight", True, config["preflight_modules"])
    # L6. Loopback self-connect proof, before any in-sandbox service.
    try:
        status_line(config, "loopback-proof", True, loopback_proof())
    except Exception as exc:  # noqa: BLE001
        fail_launcher(config, "loopback-proof", repr(exc))
    # L7. Capability proof of the final process.
    st = read_proc_status()
    cap_eff, cap_bnd = int(st["CapEff"], 16), int(st["CapBnd"], 16)
    if cap_eff != 0 or cap_bnd != 0 or st.get("NoNewPrivs") != "1":
        fail_launcher(config, "capability-proof", "CapEff=%s CapBnd=%s NoNewPrivs=%s" % (st["CapEff"], st["CapBnd"], st.get("NoNewPrivs")))
    if os.geteuid() != config["expect_uid"]:
        fail_launcher(config, "capability-proof", "uid %d, expected %d" % (os.geteuid(), config["expect_uid"]))
    status_line(config, "capability-proof", True, "CapEff=%s CapBnd=%s NoNewPrivs=1 uid=%d" % (st["CapEff"], st["CapBnd"], os.geteuid()))
    # L8. Seccomp: the bwrap route loaded it; the plain route installs it now.
    if platform.machine() != SECCOMP_ARCH:
        fail_launcher(config, "seccomp", "no filter for the architecture %s" % platform.machine())
    program = build_seccomp_x86_64()
    if hashlib.sha256(program).hexdigest() != PINNED_SECCOMP_SHA256:
        fail_launcher(config, "seccomp", "the generated filter does not match the pinned digest")
    if route == "plain":
        try:
            install_seccomp(program)
        except OSError as exc:
            fail_launcher(config, "seccomp", repr(exc))
    if read_proc_status().get("Seccomp") != "2":
        fail_launcher(config, "seccomp", "the filter is not active")
    status_line(config, "seccomp", True, "sha256=%s arch=%s route=%s" % (PINNED_SECCOMP_SHA256, SECCOMP_ARCH, route))
    # L9. AF_VSOCK canary (creation only, never a connect), after the filter and before the stub.
    try:
        status_line(config, "vsock-canary", True, vsock_blocked())
    except Exception as exc:  # noqa: BLE001
        fail_launcher(config, "vsock-canary", repr(exc))
    # L10. Synthetic /etc proof, with the filter active.
    try:
        name = pwd.getpwuid(os.getuid()).pw_name
        resolved = socket.getaddrinfo("localhost", None, socket.AF_INET)[0][4][0]
        if name != SANDBOX_USER or resolved != "127.0.0.1" or os.path.exists("/etc/resolv.conf"):
            raise RuntimeError("user=%s localhost=%s resolv.conf=%s" % (name, resolved, os.path.exists("/etc/resolv.conf")))
    except Exception as exc:  # noqa: BLE001
        fail_launcher(config, "synthetic-etc", repr(exc))
    status_line(config, "synthetic-etc", True, "user=%s" % name)
    # L11. Inside service: the NeuroForge stub (it runs unguarded), with an identity check before pytest starts.
    stub = subprocess.Popen(
        [config["python"], os.path.join(config["run_dir"], "guard", "stub_neuroforge.py"),
         "--port", str(config["stub_port"]), "--run-id", config["run_id"]],
        env=config["launcher_env"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        answer, deadline = None, time.time() + 15
        while time.time() < deadline and answer is None:
            try:
                answer = http_get_health(config["stub_port"])
            except Exception:  # noqa: BLE001
                time.sleep(0.2)
        if not answer or answer.get("run_id") != config["run_id"] or answer.get("service") != "neuroforge-stub":
            fail_launcher(config, "stub-identity", "the stub did not answer with the run identifier: %r" % (answer,))
        status_line(config, "stub-identity", True, "port=%d" % config["stub_port"])
        # L12. The PostgreSQL identity check from inside (the marker that the runner wrote).
        if config.get("postgres"):
            try:
                import psycopg2

                connection = psycopg2.connect(host=config["postgres"]["socket_dir"], user=config["postgres"]["role"],
                                              dbname="postgres", connect_timeout=10)
                cursor = connection.cursor()
                cursor.execute("SELECT run_id FROM dfiso_marker")
                marker = cursor.fetchone()[0]
                connection.close()
                if marker != config["postgres"]["marker"]:
                    raise RuntimeError("marker %r" % marker)
            except Exception as exc:  # noqa: BLE001
                fail_launcher(config, "postgres-identity", repr(exc))
            status_line(config, "postgres-identity", True, "marker=%s" % marker)
        # L13. Optional migration, under the guard (unverified here: it imports the application).
        if config.get("migrate"):
            migrated = subprocess.run([config["python"], "-m", "alembic", "upgrade", "head"], env=config["test_env"], cwd=config["repo"])
            if migrated.returncode != 0:
                fail_launcher(config, "migrate", "alembic exited %d" % migrated.returncode)
            status_line(config, "migrate", True, "head")
        # L14. Start pytest with the guard directory first on PYTHONPATH.
        status_line(config, "ready", True, "starting pytest")
        result = subprocess.run(config["pytest_command"], env=config["test_env"], cwd=config["repo"])
        status_line(config, "pytest-exit", True, str(result.returncode))
        return result.returncode
    finally:
        # L15. Stop the stub.
        stub.terminate()
        try:
            stub.wait(timeout=10)
        except subprocess.TimeoutExpired:
            stub.kill()


# ---------------------------------------------------------------------------
# Host side
# ---------------------------------------------------------------------------

def say(message: str) -> None:
    sys.stderr.write("[isolated-runner] %s\n" % message)
    sys.stderr.flush()


def tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise Precondition("the program %s is not installed" % name)
    return path


def probe_route(route: str, simulate_failure: bool) -> str:
    """Return the route that works. Raise Precondition if none does. No sudo route."""
    if simulate_failure:
        raise Precondition("namespace creation was forced to fail (--simulate-namespace-failure)")
    errors = []
    if route in ("auto", "bwrap"):
        try:
            bwrap = tool("bwrap")
            probe = subprocess.run(
                [bwrap, "--unshare-user", "--unshare-net", "--unshare-pid", "--ro-bind", "/usr", "/usr",
                 "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
                 "/usr/bin/true"], capture_output=True, text=True)
            if probe.returncode == 0:
                return "bwrap"
            errors.append("bwrap: " + probe.stderr.strip()[:200])
        except Precondition as exc:
            errors.append(str(exc))
    if route in ("auto", "plain"):
        try:
            tool("unshare"), tool("setpriv"), tool("ip")
            probe = subprocess.run(["unshare", "-rnmpf", "--propagation", "private", "true"], capture_output=True, text=True)
            if probe.returncode == 0:
                return "plain"
            errors.append("unshare: " + probe.stderr.strip()[:200])
        except Precondition as exc:
            errors.append(str(exc))
    raise Precondition("no namespace route works (%s); Docker --internal is the documented fallback" % "; ".join(errors))


def sanitized_test_env(run_dir: str, run_id: str, stub_port: int, pg: "dict | None", database: str, uid_home: str = "/tmp") -> dict:
    """The environment of the test process: built from nothing (layer 3)."""
    env = {
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "HOME": uid_home, "LANG": "C.UTF-8", "TMPDIR": "/tmp",
        "PYTHONPATH": os.path.join(run_dir, "guard"),
        "PYTHONPYCACHEPREFIX": "/tmp/pyc", "COVERAGE_FILE": "/tmp/.coverage",
        "PYTHONUNBUFFERED": "1",
        "NETGUARD_RUN_ID": run_id, "NETGUARD_MANIFEST": os.path.join(run_dir, "manifest.json"),
        "NETGUARD_GUARD_DIR": os.path.join(run_dir, "guard"),
        "NETGUARD_SECCOMP_SHA256": PINNED_SECCOMP_SHA256, "NETGUARD_SECCOMP_ARCH": SECCOMP_ARCH,
        "NEUROFORGE_URL": "http://127.0.0.1:%d" % stub_port,
        "REDIS_URL": "unix://%s" % os.path.join(run_dir, "redis-absent.sock"),
        "SUPABASE_API_BASE": "https://supabase.invalid",
        "SUPABASE_ACCESS_TOKEN": "", "SUPABASE_PROJECT_REF": "",
        "DATAFORGE_TELEMETRY_API_KEY": "", "DATAFORGE_TELEMETRY_BASE_URL": "",
        "DATAFORGE_TELEMETRY_DATABASE_URL": "", "DATAFORGE_TELEMETRY_SPOOL_PATH": "",
        "VOYAGE_API_KEY": "test-key",
        "DATAFORGE_DATABASE_URL": "sqlite:///:memory:",
        "DATAFORGE_RLS_TEST_POSTGRES_URL": "", "CLOUD_IMAGE_TEST_POSTGRES_URL": "",
    }
    if pg:
        base = "postgresql://%s@/%%s?host=%s" % (pg["role"], pg["socket_dir"])
        env["DATAFORGE_RLS_TEST_POSTGRES_URL"] = base % "postgres"
        env["CLOUD_IMAGE_TEST_POSTGRES_URL"] = base % "postgres"
        if database == "postgres":
            env["DATAFORGE_DATABASE_URL"] = base % "dataforge_test"
    return {k: v for k, v in env.items() if v != "" or k.startswith(("DATAFORGE_", "SUPABASE_"))}


def write_run_files(run_dir: str, run_id: str, manifest: dict, stub_port: int, uid: int, gid: int) -> None:
    os.makedirs(run_dir + "/etc")
    Path(run_dir, "etc", "hosts").write_text("127.0.0.1 localhost\n::1 localhost\n")
    Path(run_dir, "etc", "nsswitch.conf").write_text("hosts: files\npasswd: files\ngroup: files\n")
    Path(run_dir, "etc", "passwd").write_text("%s:x:%d:%d:dftest:/tmp:/bin/bash\n" % (SANDBOX_USER, uid, gid))
    Path(run_dir, "etc", "group").write_text("%s:x:%d:\n" % (SANDBOX_USER, gid))
    os.makedirs(run_dir + "/guard")
    for name in GUARD_FILES:
        shutil.copy2(ISOLATION_DIR / name, run_dir + "/guard/" + name)
    for name in os.listdir(run_dir + "/guard"):
        os.chmod(os.path.join(run_dir, "guard", name), 0o444)
    os.makedirs(run_dir + "/viol", mode=0o700)
    os.makedirs(run_dir + "/log", mode=0o700)
    Path(run_dir, "viol", "violations.jsonl").touch(mode=0o600)
    Path(run_dir, "log", "declared_absent.jsonl").touch(mode=0o600)
    Path(run_dir, "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))


def make_manifest(run_dir: str, run_id: str, stub_port: int, pg_socket: "str | None") -> dict:
    return {
        "version": 1, "run_id": run_id,
        "violations_path": os.path.join(run_dir, "viol", "violations.jsonl"),
        "declared_absent_log": os.path.join(run_dir, "log", "declared_absent.jsonl"),
        "log_dir": os.path.join(run_dir, "log"),
        "tcp": [{"host": "127.0.0.1", "port": stub_port, "service": "neuroforge-stub"}],
        "unix": [{"path": pg_socket, "service": "postgres"}] if pg_socket else [],
        "declared_absent": [{"service": "redis", "path": os.path.join(run_dir, "redis-absent.sock"), "reason": REDIS_ABSENT_REASON}],
        "programs": ["python*", "bash", "sh", "git", "openssl"],
        "declared_skip_patterns": [],
    }


def validate_manifest(manifest: dict, run_dir: str) -> None:
    """Refuse a manifest entry that is not a service of this run (no external DSN, no foreign path)."""
    for entry in manifest["tcp"]:
        if entry["host"] != "127.0.0.1" or not 1024 <= int(entry["port"]) <= 65535:
            raise Precondition("manifest entry %r is not a loopback service" % (entry,))
    for entry in [*manifest["unix"], *manifest["declared_absent"]]:
        if os.path.dirname(entry["path"]) not in (run_dir, os.path.join(run_dir, "pg")) or not entry["path"].startswith(run_dir + "/"):
            raise Precondition("manifest entry %r is outside the run directory" % (entry,))


class RecordError(Exception):
    """A record file is missing, replaced or unparseable. The runner exits 87."""


def read_jsonl_strict(path: str, held_fd: "int | None" = None) -> list:
    """Read a JSON-lines file. With `held_fd`, read through the descriptor that the runner opened
    before the launch, and require that the path still names the same file."""
    try:
        if held_fd is not None:
            if os.stat(path).st_ino != os.fstat(held_fd).st_ino:
                raise RecordError("%s is not the file that the runner opened" % path)
            os.lseek(held_fd, 0, os.SEEK_SET)
            chunks = []
            while True:
                chunk = os.read(held_fd, 1 << 20)
                if not chunk:
                    break
                chunks.append(chunk)
            text = b"".join(chunks).decode("utf-8")
        else:
            text = Path(path).read_text(encoding="utf-8")
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    except RecordError:
        raise
    except (OSError, ValueError) as exc:
        raise RecordError("%s: %r" % (path, exc))


class Tee(threading.Thread):
    """Copy one sandbox stream to ours and count the guard's marker lines (a second, weaker channel).

    Pytest captures the output of a passing test, so this channel can miss a violation.
    The record file is the authority.
    """

    def __init__(self, stream, sink):
        super().__init__(daemon=True)
        self.stream, self.sink, self.markers = stream, sink, 0

    def run(self):
        for raw in iter(self.stream.readline, b""):
            if raw.startswith((b"NETGUARD-VIOLATION", b"NETGUARD-FATAL")):
                self.markers += 1
            self.sink.buffer.write(raw)
            self.sink.buffer.flush()


def parse_args(argv: list) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="run-tests-isolated.sh", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--route", choices=("auto", "bwrap", "plain"), default="auto", help="namespace route (no sudo route exists)")
    parser.add_argument("--canary", action="store_true", help="run the sandbox canary suite instead of the test suite")
    parser.add_argument("--database", choices=("sqlite", "postgres"), default="sqlite", help="database of the application under test")
    parser.add_argument("--migrate", action="store_true", help="run alembic upgrade head in the sandbox first (needs --database postgres)")
    parser.add_argument("--no-postgres", action="store_true", help="do not start the disposable PostgreSQL")
    parser.add_argument("--report", help="write the JSON report to this host path")
    parser.add_argument("--keep-run-dir", action="store_true", help="keep the run directory after a clean run")
    parser.add_argument("--stub-port", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--simulate-namespace-failure", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--preflight-modules", default=DEFAULT_PREFLIGHT_MODULES, help=argparse.SUPPRESS)
    parser.add_argument("--debug-omit-interpreter-trees", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--debug-fail-postgres-readiness", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("pytest_args", nargs="*")
    args = parser.parse_args(argv)
    if args.migrate and args.database != "postgres":
        parser.error("--migrate needs --database postgres")
    if args.database == "postgres" and args.no_postgres:
        parser.error("--database postgres needs the disposable PostgreSQL")
    return args


def check_preconditions(args: argparse.Namespace) -> str:
    if sys.platform != "linux":
        raise Precondition("Linux is required")
    if platform.machine() != SECCOMP_ARCH:
        raise Precondition("the seccomp filter covers %s only; this host is %s" % (SECCOMP_ARCH, platform.machine()))
    if os.geteuid() == 0:
        raise Precondition("the runner refuses to run as real root")
    if seccomp_digest() != PINNED_SECCOMP_SHA256:
        raise Precondition("the seccomp generator does not match its pinned digest (%s)" % seccomp_digest())
    dotenv = find_dotenv_files(REPO)
    if dotenv:
        raise Precondition("a .env file exists (load_dotenv would read it): %s" % ", ".join(dotenv))
    proxies = proxy_variables_set(os.environ)
    if proxies:
        raise Precondition("a proxy variable is set: %s" % ", ".join(proxies))
    for name in GUARD_FILES:
        if not (ISOLATION_DIR / name).is_file():
            raise Precondition("missing %s" % (ISOLATION_DIR / name))
    if not args.no_postgres:
        tool("docker")
        sys.path.insert(0, str(ISOLATION_DIR))
        import services

        try:
            services.check_docker_local(os.environ)
        except services.ServiceError as exc:
            raise Precondition("docker: %s" % exc)
    return probe_route(args.route, args.simulate_namespace_failure)


def launch(args, route, run_dir, config, plan, seccomp_program) -> "tuple[int, Tee]":
    launch_json = os.path.join(run_dir, "launch.json")
    Path(launch_json).write_text(json.dumps(config, indent=1, sort_keys=True))
    host_env = dict(config["launcher_env"])
    runner = str(REPO / "scripts" / "isolated_test_runner.py")
    pass_fds = ()
    if route == "bwrap":
        seccomp_path = os.path.join(run_dir, "seccomp.bpf")
        Path(seccomp_path).write_bytes(seccomp_program)
        fd = os.open(seccomp_path, os.O_RDONLY)
        pass_fds = (fd,)
        command = bwrap_args(plan, fd, REPO) + [config["python"], runner, "--internal-stage2", launch_json]
    else:
        command = ["unshare", "-rnmpf", "--propagation", "private", config["python"], runner, "--internal-stage1", launch_json]
    proc = subprocess.Popen(command, env=host_env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, pass_fds=pass_fds, cwd=str(REPO))
    tee_err, tee_out = Tee(proc.stderr, sys.stderr), Tee(proc.stdout, sys.stdout)
    tee_err.start()
    tee_out.start()

    def forward(signum, _frame):
        try:
            proc.send_signal(signum)
        except ProcessLookupError:
            pass

    old = [signal.signal(s, forward) for s in (signal.SIGINT, signal.SIGTERM)]
    try:
        rc = proc.wait()
    finally:
        for s, handler in zip((signal.SIGINT, signal.SIGTERM), old):
            signal.signal(s, handler)
    tee_err.join(timeout=5)
    tee_out.join(timeout=5)
    if pass_fds:
        os.close(pass_fds[0])
    tee_err.markers += tee_out.markers
    return rc, tee_err


def run_once(args: argparse.Namespace, state: dict) -> int:
    """Steps 1 to 8 of section 4.5 (the sandbox itself runs L1 to L15 above). Return the exit code."""
    run_id = state["run_id"]
    run_dir = state["run_dir"]
    report = state["report"]
    try:
        # 1. Preconditions (any failure is exit 86 and no test starts).
        route = check_preconditions(args)
        # 2. Run directory, stub port, manifest.
        stub_port = choose_stub_port(args.stub_port)
        if os.path.exists(run_dir):
            raise Precondition("a stale run directory exists: " + run_dir)
        os.mkdir(run_dir, 0o700)
        uid, gid = (os.getuid(), os.getgid()) if route == "bwrap" else (0, 0)
        report.update(route=route, stub_port=stub_port, seccomp_sha256=PINNED_SECCOMP_SHA256, seccomp_arch=SECCOMP_ARCH)
        pg = None
        socket_dir = os.path.join(run_dir, "pg")
        if not args.no_postgres:
            os.mkdir(socket_dir)
        sys.path.insert(0, str(ISOLATION_DIR))
        import services  # noqa: E402 - the disposable PostgreSQL (host side only)

        pg_socket = os.path.join(socket_dir, services.SOCKET_NAME) if not args.no_postgres else None
        if pg_socket and len(pg_socket) > 100:
            raise Precondition("the socket path is too long for sun_path: " + pg_socket)
        manifest = make_manifest(run_dir, run_id, stub_port, pg_socket)
        validate_manifest(manifest, run_dir)
        write_run_files(run_dir, run_id, manifest, stub_port, uid, gid)
        # 3. Outside services: the container, and its identity checked from outside.
        if not args.no_postgres:
            role = SANDBOX_USER  # no password exists: see the "no secret" note in doc/system/15-testing.md
            try:
                state["pg_record"] = services.start_postgres(run_id, socket_dir, role,
                                                             fail_after_run=args.debug_fail_postgres_readiness)
                record = state["pg_record"]
                identity = services.verify_identity_outside(record, run_id)
                if args.database == "postgres":
                    services.create_database(record, "dataforge_test")
            except services.ServiceError as exc:
                raise Precondition("postgres: %s" % exc)
            pg = {"role": role, "socket_dir": socket_dir, "marker": re.sub(r"[^0-9a-f]", "", run_id)}
            report["postgres"] = {**{k: record[k] for k in ("container_id", "image", "image_id")}, **identity}
        for name in WRITABLE_REPO_FILES:
            (REPO / name).touch(exist_ok=True)
        for name in ("htmlcov",):
            (REPO / name).mkdir(exist_ok=True)
        plan = build_plan(run_dir, REPO, not args.no_postgres, os.path.join(run_dir, "etc"),
                          omit_interpreter_trees=args.debug_omit_interpreter_trees)
        python = sys.executable
        launcher_env = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "HOME": "/tmp", "LANG": "C.UTF-8", "TMPDIR": "/tmp"}
        if os.path.dirname(python) not in launcher_env["PATH"].split(":"):
            launcher_env["PATH"] = os.path.dirname(python) + ":" + launcher_env["PATH"]
        test_env = sanitized_test_env(run_dir, run_id, stub_port, pg, args.database)
        test_env["PATH"] = launcher_env["PATH"]
        if args.canary:
            canary = str(ISOLATION_DIR / "canary" / "sandbox")
            pytest_args = [canary, "--confcutdir", canary, "-c", str(REPO / "pytest.ini"), "--rootdir", str(REPO),
                           "-o", "addopts=", "-o", "python_files=check_*.py", "--strict-markers", "-v", "--tb=short"]
        else:
            pytest_args = args.pytest_args or ["tests"]
        config = {
            "run_id": run_id, "run_dir": run_dir, "log_dir": os.path.join(run_dir, "log"), "repo": str(REPO),
            "route": route, "python": python, "plan": plan, "launcher_env": launcher_env, "test_env": test_env,
            "stub_port": stub_port, "expect_uid": uid, "postgres": pg, "migrate": args.migrate,
            "preflight_modules": args.preflight_modules,
            "pytest_command": [python, "-m", "pytest", "-p", "pytest_plugin", "-p", "no:cacheprovider", *pytest_args],
        }
        say("route=%s run=%s uid-in-sandbox=%d" % (route, run_id, uid))
        # 4. The in-sandbox launcher (without the guard) runs L1 to L15, which include pytest.
        state["viol_fd"] = os.open(os.path.join(run_dir, "viol", "violations.jsonl"), os.O_RDONLY)
        rc, tee = launch(args, route, run_dir, config, plan, build_seccomp_x86_64())
    except Precondition as exc:
        say("PRECONDITION FAILED: %s" % exc)
        report["precondition_error"] = str(exc)
        return EXIT_PRECONDITION
    # 8. Read the records after pytest exits (step 5 to 7 ran in the sandbox).
    try:
        violations = read_jsonl_strict(os.path.join(run_dir, "viol", "violations.jsonl"), state["viol_fd"])
    except RecordError as exc:
        say("the violation record is unusable: %s" % exc)
        report["record_error"] = str(exc)
        return EXIT_VIOLATION
    # A guard violation counts even if the sandbox never reached pytest (for example during --migrate).
    if violations or tee.markers:
        report.update(launcher_exit=rc, violations=len(violations), stderr_markers=tee.markers)
        say("%d violation(s) in violations.jsonl, %d marker(s) on output" % (len(violations), tee.markers))
        return EXIT_VIOLATION
    try:
        status = read_jsonl_strict(os.path.join(run_dir, "log", "status.jsonl"))
    except RecordError:
        status = []  # a missing status file means the launcher never started
    steps = {s["step"] for s in status if s.get("ok")}
    try:
        absent = read_jsonl_strict(os.path.join(run_dir, "log", "declared_absent.jsonl"))
    except RecordError as exc:
        say("the declared-absent log is unusable: %s" % exc)
        return EXIT_VIOLATION
    skips, skip_files = [], 0
    for name in sorted(os.listdir(os.path.join(run_dir, "log"))):
        if name.startswith("skips-"):
            skip_files += 1
            try:
                skips += json.loads(Path(run_dir, "log", name).read_text())["skips"]
            except (OSError, ValueError, KeyError) as exc:
                say("the skip report %s is unusable: %r" % (name, exc))
                return EXIT_VIOLATION
    undeclared = [s for s in skips if not s["declared"]]
    report.update(
        launcher_exit=rc, status=status, violations=0, stderr_markers=tee.markers,
        declared_absent_probes=len(absent), declared_absent_services=sorted({a["service"] for a in absent}),
        skips_total=len(skips), skips_declared=len(skips) - len(undeclared), skips_undeclared=undeclared[:200],
    )
    if "ready" not in steps:
        failed = [s for s in status if not s.get("ok")]
        say("the sandbox did not reach pytest: %s" % (failed[-1] if failed else "no status written (launch failed)"))
        return EXIT_PRECONDITION
    if rc in (0, 1) and skip_files == 0:
        say("pytest exited %d but wrote no skip report; undeclared skips cannot be excluded" % rc)
        return EXIT_VIOLATION
    if undeclared:
        say("%d skip(s) with no declared reason" % len(undeclared))
        return EXIT_VIOLATION
    return rc


def _interrupt(signum, _frame):
    raise KeyboardInterrupt("signal %d" % signum)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "--internal-stage1":
        return stage1(argv[1])
    if argv and argv[0] == "--internal-stage2":
        return stage2(argv[1])
    args = parse_args(argv)
    sys.path.insert(0, str(ISOLATION_DIR))  # services must import in the cleanup, whatever failed first
    signal.signal(signal.SIGTERM, _interrupt)  # teardown must run on SIGTERM and SIGINT
    signal.signal(signal.SIGINT, _interrupt)
    run_id = secrets.token_hex(4)
    state = {"run_id": run_id, "run_dir": os.path.join(RUN_PARENT, "dfi-" + run_id), "pg_record": None,
             "viol_fd": None, "report": {"run_id": run_id}}
    code = EXIT_PRECONDITION
    try:
        code = run_once(args, state)
    except KeyboardInterrupt as exc:
        say("interrupted (%s)" % exc)
        code = EXIT_PRECONDITION
    finally:
        # 9. Teardown: the container by its fixed name (even if start_postgres raised), then the run directory.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        clean = True
        if not args.no_postgres:
            try:
                import services

                if services._DOCKER_ENV:  # the docker client passed the local-endpoint check
                    clean = services.remove_container(services.container_name(run_id), os.path.join(state["run_dir"], "pg"))
                    if not clean:
                        say("TEARDOWN FAILED: container %s remains" % services.container_name(run_id))
            except Exception as exc:  # noqa: BLE001 - a cleanup fault must not mask the real exit code
                clean = False
                say("TEARDOWN FAILED: %r" % (exc,))
        if state["viol_fd"] is not None:
            os.close(state["viol_fd"])
        if not clean and code not in (EXIT_PRECONDITION, EXIT_VIOLATION):
            code = EXIT_TEARDOWN
        report = state["report"]
        report.update(teardown_clean=clean, exit_code=code, run_dir=state["run_dir"])
        if args.report:
            try:
                Path(args.report).write_text(json.dumps(report, indent=1, sort_keys=True, default=str))
            except OSError as exc:
                say("cannot write the report %s: %r" % (args.report, exc))
                if code == 0:
                    code = EXIT_TEARDOWN
        run_dir = state["run_dir"]
        if os.path.isdir(run_dir):
            if code == 0 and clean and not args.keep_run_dir:
                shutil.rmtree(run_dir, ignore_errors=True)
                if os.path.exists(run_dir):
                    say("the run directory could not be removed: " + run_dir)
            else:
                say("run directory kept: %s" % run_dir)
    return code


if __name__ == "__main__":
    sys.exit(main())
