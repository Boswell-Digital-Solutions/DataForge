"""Layer 1 and the sandbox itself: namespaces, mounts, privilege, filter, environment."""

import ctypes
import errno
import grp
import importlib.util
import json
import os
import pwd
import socket
import subprocess
import sys

import pytest

from canary_support import DOC_ADDRESS, REPO, run_unguarded

pytestmark = pytest.mark.isolation_canary

MANIFEST = json.load(open(os.environ["NETGUARD_MANIFEST"]))


def status() -> dict:
    out = {}
    for line in open("/proc/self/status"):
        key, _, rest = line.partition(":")
        out[key] = rest.strip()
    return out


def test_documentation_address_is_unreachable_without_the_guard():
    result = run_unguarded(
        "import socket,sys\n"
        "s=socket.socket(); s.settimeout(3)\n"
        f"try:\n    s.connect(('{DOC_ADDRESS}',80))\nexcept OSError as e:\n    print(e.errno, e.strerror); sys.exit(0)\n"
        "print('CONNECTED'); sys.exit(3)\n")
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.startswith("101 "), result.stdout  # Network is unreachable


def test_only_a_loopback_interface_exists():
    names = {line.split(":")[0].strip() for line in open("/proc/net/dev").read().splitlines()[2:]}
    assert names == {"lo"}


def test_bash_and_curl_cannot_reach_the_documentation_address():
    bash = subprocess.run(["bash", "-c", f"exec 3<>/dev/tcp/{DOC_ADDRESS}/80"], capture_output=True, text=True, timeout=20)
    assert bash.returncode != 0 and "unreachable" in bash.stderr.lower(), bash.stderr
    curl = subprocess.run(["bash", "-c", f"curl -sS --max-time 5 http://{DOC_ADDRESS}/ 2>&1; echo rc=$?"], capture_output=True, text=True, timeout=30)
    assert "unreachable" in curl.stdout.lower() or "rc=7" in curl.stdout, curl.stdout


def test_root_is_an_allow_list_and_forbidden_sockets_are_absent():
    top = set(os.listdir("/"))
    assert top <= {"bin", "sbin", "lib", "lib32", "lib64", "libx32", "usr", "etc", "proc", "dev", "tmp", "home", "opt", "var"}, top
    for forbidden in ("run", "var/run", "var/lib", "root", "srv", "mnt", "media", "boot", "sys"):
        assert not os.path.exists("/" + forbidden), forbidden
    assert sorted(os.listdir("/etc")) == ["group", "hosts", "nsswitch.conf", "passwd"]
    for path in ("/var/run/docker.sock", "/run/docker.sock", "/var/run/postgresql", "/run/user", "/run/dbus", "/etc/resolv.conf"):
        assert not os.path.exists(path), path


def test_environment_is_sanitized():
    for name in ("PGHOST", "DOCKER_HOST", "SSH_AUTH_SOCK", "DBUS_SESSION_BUS_ADDRESS", "HTTP_PROXY", "HTTPS_PROXY",
                 "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "all_proxy", "no_proxy"):
        assert name not in os.environ, name
    stub = MANIFEST["tcp"][0]["port"]
    assert os.environ["NEUROFORGE_URL"] == f"http://127.0.0.1:{stub}"
    assert os.environ["REDIS_URL"].startswith("unix://") and os.environ["REDIS_URL"].endswith("redis-absent.sock")
    assert os.environ["SUPABASE_API_BASE"] == "https://supabase.invalid"
    assert os.environ["DATAFORGE_TELEMETRY_BASE_URL"] == ""


def test_mounts_are_read_only_where_the_design_says():
    for path in ("/canary-write", "/usr/canary-write", "/etc/canary-write", "/home/canary-write",
                 os.path.join(os.environ["NETGUARD_GUARD_DIR"], "canary-write"), str(REPO / "canary-write")):
        with pytest.raises(OSError) as exc:
            open(path, "w")
        assert exc.value.errno in (errno.EROFS, errno.EACCES, errno.EPERM), (path, exc.value)
    for path in ("/etc/hosts", "/etc/passwd", os.environ["NETGUARD_MANIFEST"], os.path.join(os.environ["NETGUARD_GUARD_DIR"], "netguard.py")):
        with pytest.raises(OSError):
            open(path, "a")


def test_the_violation_record_is_a_mount_point_that_cannot_be_unlinked():
    mounts = open("/proc/self/mountinfo").read()
    points = {line.split()[4] for line in mounts.splitlines()}
    record = MANIFEST["violations_path"]
    assert record in points and MANIFEST["log_dir"] in points
    for operation in (lambda: os.unlink(record), lambda: os.rename(record, record + ".moved")):
        with pytest.raises(OSError):
            operation()
    assert os.path.exists(record)


def _classify(pid: int) -> list:
    import stat

    bad = []
    null = os.stat("/dev/null")
    for name in os.listdir(f"/proc/{pid}/fd"):
        try:
            st = os.stat(f"/proc/{pid}/fd/{name}")
            link = os.readlink(f"/proc/{pid}/fd/{name}")
        except OSError:
            continue
        if stat.S_ISREG(st.st_mode) or stat.S_ISFIFO(st.st_mode) or link.startswith(("pipe:", "anon_inode:")):
            continue
        if stat.S_ISCHR(st.st_mode) and st.st_rdev == null.st_rdev:
            continue
        bad.append((pid, name, link))
    return bad


def test_no_socket_and_no_terminal_descriptor_crossed_into_the_sandbox():
    """Descriptors of every ancestor of this process and the startup snapshot of the guard."""
    pid, chain = os.getppid(), []
    while pid > 0:
        chain.append(pid)
        fields = open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()
        pid = int(fields[1])
    assert chain, "no ancestor visible"
    readable = 0
    for ancestor in chain:
        try:
            problems = _classify(ancestor)
            stdin = os.readlink(f"/proc/{ancestor}/fd/0")
        except PermissionError:
            continue  # the plain route's pid 1 holds capabilities in its user namespace and is not readable
        readable += 1
        assert problems == [], ancestor
        assert stdin == "/dev/null", ancestor  # stdin is /dev/null, never a socket
    assert readable >= 1
    snapshot = json.load(open(os.path.join(MANIFEST["log_dir"], "snapshot-%d.json" % os.getpid())))
    assert snapshot["inherited_fd_problems"] == []


def test_privilege_rule():
    st = status()
    assert int(st["CapEff"], 16) == 0 and int(st["CapBnd"], 16) == 0 and st["NoNewPrivs"] == "1"
    libc = ctypes.CDLL(None, use_errno=True)
    assert libc.unshare(0x40000000) == -1 and ctypes.get_errno() == errno.EPERM  # CLONE_NEWNET
    fd = os.open("/proc/self/ns/net", os.O_RDONLY)
    assert libc.setns(fd, 0x40000000) == -1 and ctypes.get_errno() == errno.EPERM
    os.close(fd)


def test_synthetic_etc_and_resolution():
    assert pwd.getpwuid(os.getuid()).pw_name == "dftest"
    assert grp.getgrgid(os.getgid()).gr_name == "dftest"
    assert socket.getaddrinfo("localhost", None, socket.AF_INET)[0][4][0] == "127.0.0.1"
    assert socket.gethostbyname("localhost") == "127.0.0.1"


def test_interpreter_and_programs_are_present():
    result = subprocess.run([sys.executable, "-c", "import ssl, sqlite3, json"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    for command in (["bash", "--version"], ["git", "--version"], ["openssl", "version"]):
        assert subprocess.run(command, capture_output=True).returncode == 0, command


def test_git_works_in_the_sandbox():
    result = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True)
    assert result.returncode == 0 and len(result.stdout.strip()) == 40, result.stderr


def test_seccomp_filter_is_active_and_matches_its_pin():
    assert status()["Seccomp"] == "2"
    libc = ctypes.CDLL(None, use_errno=True)

    def family(f, t=1):
        fd = libc.socket(f, t, 0)
        err = ctypes.get_errno()
        if fd >= 0:
            os.close(fd)
        return fd >= 0, err

    assert family(1)[0] and family(2)[0] and family(10)[0]
    for denied, kind in ((40, 1), (16, 3), (17, 3), (38, 1)):  # vsock, netlink, packet, alg
        assert family(denied, kind) == (False, errno.EAFNOSUPPORT), denied
    assert libc.syscall(425, 0, 0) == -1 and ctypes.get_errno() == errno.EPERM  # io_uring_setup
    assert libc.syscall(426, 0, 0, 0, 0, 0) == -1 and ctypes.get_errno() == errno.EPERM
    assert libc.syscall(427, 0, 0, 0, 0) == -1 and ctypes.get_errno() == errno.EPERM
    assert libc.syscall(41 | 0x40000000, 2, 1, 0) == -1 and ctypes.get_errno() == errno.EPERM  # x32 ABI
    spec = importlib.util.spec_from_file_location("runner", REPO / "scripts" / "isolated_test_runner.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    assert runner.seccomp_digest() == os.environ["NETGUARD_SECCOMP_SHA256"] == runner.PINNED_SECCOMP_SHA256
    assert os.environ["NETGUARD_SECCOMP_ARCH"] == "x86_64"


def test_no_vsock_device():
    assert not os.path.exists("/dev/vsock")
    assert set(os.listdir("/dev")) <= {"null", "zero", "full", "random", "urandom", "tty", "shm", "fd", "stdin", "stdout", "stderr", "pts", "ptmx", "console", "core"}
