"""Canaries of the runner itself, run from the host (not in the sandbox, not under the runner):

    python -m pytest tests/isolation/canary/host -c pytest.ini -o addopts= -o python_files='check_*.py' \
        --confcutdir tests/isolation/canary/host -p no:cacheprovider

They do not import `app` and do not run the DataForge suite. The conftest gate is tested on a
copy of tests/conftest.py next to a poison `app` package, so the real application cannot load.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.isolation_canary

REPO = Path(__file__).resolve().parents[4]
RUNNER = REPO / "scripts" / "isolated_test_runner.py"
PLANTED_ROOT = REPO / "tests" / "isolation" / "canary"
DOC_ADDRESS = "192.0.2.1"

spec = importlib.util.spec_from_file_location("isolated_runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def run_runner(*args, env_extra=None, timeout=300):
    env = {k: v for k, v in os.environ.items() if k not in runner.PROXY_VARIABLES}
    env.update(env_extra or {})
    return subprocess.run([sys.executable, str(RUNNER), *args], env=env, capture_output=True, text=True, timeout=timeout, cwd=str(REPO))


@pytest.fixture
def planted(request):
    """A temporary test directory inside the repository (the sandbox binds the repository)."""
    directory = Path(tempfile.mkdtemp(prefix="planted_", dir=PLANTED_ROOT))
    yield directory
    shutil.rmtree(directory, ignore_errors=True)


def pytest_args_for(directory: Path, filename: str = "check_planted.py"):
    return ["--", str(directory / filename), "--confcutdir", str(directory), "-c", str(REPO / "pytest.ini"),
            "--rootdir", str(REPO), "-o", "addopts=", "-o", "python_files=check_*.py"]


def write_test(directory: Path, source: str):
    (directory / "check_planted.py").write_text(textwrap.dedent(source))


# ---- the conftest gate -----------------------------------------------------------------------

def test_the_gate_precedes_every_third_party_and_app_import_in_the_real_conftest():
    tree = ast.parse((REPO / "tests" / "conftest.py").read_text())
    gate_line = next(n.lineno for n in tree.body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                     and getattr(n.value.func, "id", "") == "_refuse_direct_pytest")
    stdlib = set(sys.stdlib_module_names)
    for node in tree.body:
        names = []
        if isinstance(node, ast.Import):
            names = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module.split(".")[0]]
        for name in names:
            if node.lineno < gate_line:
                assert name in stdlib, f"{name} is imported before the gate"
            if name in ("app", "fastapi", "sqlalchemy", "pytest"):
                assert node.lineno > gate_line


@pytest.mark.parametrize("flags", [[], ["--collect-only", "-q"]])
@pytest.mark.parametrize("env_extra", [{}, {"NETGUARD_RUN_ID": "forged"}])
def test_direct_pytest_is_refused_with_exit_87_and_the_application_never_loads(tmp_path, flags, env_extra):
    marker = tmp_path / "APP-WAS-IMPORTED"
    poison = tmp_path / "poison" / "app"
    poison.mkdir(parents=True)
    (poison / "__init__.py").write_text(f"open({str(marker)!r}, 'w').close()\nraise SystemExit('poison app imported')\n")
    work = tmp_path / "work"
    work.mkdir()
    shutil.copy2(REPO / "tests" / "conftest.py", work / "conftest.py")
    (work / "test_x.py").write_text("def test_x():\n    assert True\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith("NETGUARD_")}
    env.update(PYTHONPATH=str(tmp_path / "poison"), **env_extra)
    result = subprocess.run([sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-o", "addopts=", *flags, str(work)],
                            env=env, capture_output=True, text=True, timeout=60, cwd=str(work))
    assert result.returncode == 87, result.stdout + result.stderr
    assert "REFUSED (exit 87)" in result.stderr
    assert not marker.exists()


# ---- the runner's preconditions (exit 86, no test starts) --------------------------------------

def test_a_forced_namespace_failure_exits_86_and_no_test_runs():
    result = run_runner("--simulate-namespace-failure", "--no-postgres", "--canary")
    assert result.returncode == 86, result.stdout + result.stderr
    assert "test session starts" not in result.stdout + result.stderr
    assert "namespace creation was forced to fail" in result.stderr


def test_a_proxy_variable_exits_86():
    result = run_runner("--no-postgres", "--canary", env_extra={"HTTPS_PROXY": "http://127.0.0.1:9"})
    assert result.returncode == 86 and "a proxy variable is set: HTTPS_PROXY" in result.stderr
    assert "test session starts" not in result.stdout + result.stderr


def test_a_stub_port_in_the_ephemeral_range_exits_86():
    low, _ = runner.ephemeral_range()
    result = run_runner("--no-postgres", "--canary", "--stub-port", str(low + 10))
    assert result.returncode == 86 and "ephemeral range" in result.stderr


def test_a_failed_interpreter_preflight_exits_86_before_pytest(planted):
    write_test(planted, "def test_ok():\n    assert True\n")
    result = run_runner("--no-postgres", "--preflight-modules", "ssl,not_a_module_xyz", *pytest_args_for(planted))
    assert result.returncode == 86, result.stdout + result.stderr
    assert "preflight-interpreter" in result.stderr and "test session starts" not in result.stdout + result.stderr


def test_a_dotenv_file_is_found_in_a_parent(tmp_path):
    (tmp_path / ".env").write_text("X=1\n")
    child = tmp_path / "a" / "b"
    child.mkdir(parents=True)
    assert runner.find_dotenv_files(child) == [str(tmp_path / ".env")]
    assert runner.find_dotenv_files(REPO) == [], "a .env exists above the repository: the runner would refuse"


def test_the_image_check_never_pulls_and_a_missing_image_is_a_service_error():
    sys.path.insert(0, str(REPO / "tests" / "isolation"))
    import services

    with pytest.raises(services.ServiceError):
        services.image_id("dfiso-canary/does-not-exist:never")
    assert "--pull=never" in (REPO / "tests" / "isolation" / "services.py").read_text()


def test_pure_helpers():
    assert runner.seccomp_digest() == runner.PINNED_SECCOMP_SHA256 and runner.SECCOMP_ARCH == "x86_64"
    assert runner.is_forbidden_tree("/") and runner.is_forbidden_tree("/var/run") and not runner.is_forbidden_tree("/usr")
    assert runner.proxy_variables_set({"http_proxy": "x", "OTHER": "y"}) == ["http_proxy"]
    low, high = runner.ephemeral_range()
    assert all(not low <= runner.choose_stub_port() <= high for _ in range(50))
    assert runner.parse_proc_status("CapEff:\t000001ffffffffff\nNoNewPrivs:\t1\n")["CapEff"] == "000001ffffffffff"
    assert "sudo" not in (REPO / "scripts" / "isolated_test_runner.py").read_text().replace("no sudo route", "").replace("sudo route", "")


# ---- end-of-run behavior of the runner ---------------------------------------------------------

@pytest.mark.parametrize("route", ["bwrap", "plain"])
def test_a_clean_planted_run_exits_0_and_tears_everything_down(planted, tmp_path, route):
    write_test(planted, "def test_ok():\n    assert 1 + 1 == 2\n")
    report = tmp_path / "report.json"
    result = run_runner("--route", route, "--report", str(report), *pytest_args_for(planted))
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(report.read_text())
    assert data["violations"] == 0 and data["route"] == route and data["teardown_clean"] is True
    assert data["postgres"]["pgvector_available"] is True
    run_id, run_dir = data["run_id"], data["run_dir"]
    assert not os.path.exists(run_dir) and not os.path.exists("/tmp/dfi-" + run_id)
    docker = subprocess.run(["docker", "ps", "-a", "--filter", f"label=dfiso.run={run_id}", "-q"], capture_output=True, text=True)
    assert docker.stdout.strip() == ""
    procs = subprocess.run(["pgrep", "-f", run_id], capture_output=True, text=True)
    assert procs.stdout.strip() == ""


def test_a_swallowed_violation_in_except_exception_fails_the_run_with_87(planted):
    write_test(planted, f"""
        import socket, pytest
        def test_swallow():
            try:
                socket.create_connection(('{DOC_ADDRESS}', 80), timeout=1)
            except Exception as e:
                pytest.skip(f'service not available: {{e}}')
    """)
    result = run_runner("--no-postgres", *pytest_args_for(planted))
    assert result.returncode == 87, result.stdout + result.stderr
    assert "1 failed" in result.stdout and "violation(s) in violations.jsonl" in result.stderr
    assert "NETGUARD-VIOLATION" in result.stdout + result.stderr


def test_a_violation_swallowed_by_except_baseexception_fails_the_run(planted):
    write_test(planted, f"""
        import socket
        def test_swallow_all():
            try:
                socket.create_connection(('{DOC_ADDRESS}', 80), timeout=1)
            except BaseException:
                pass
    """)
    result = run_runner("--no-postgres", *pytest_args_for(planted))
    assert result.returncode == 87, result.stdout + result.stderr


def test_a_violation_of_a_child_process_fails_a_run_whose_test_passes(planted):
    write_test(planted, f"""
        import subprocess, sys
        def test_child():
            subprocess.run([sys.executable, '-c', "import socket; socket.create_connection(('{DOC_ADDRESS}', 80), timeout=1)"])
    """)
    result = run_runner("--no-postgres", *pytest_args_for(planted))
    # the plugin counts the violation of the child for the test and fails it, even though the test body passes
    assert result.returncode == 87 and "1 failed" in result.stdout and "NetworkIsolationViolation" in result.stdout, result.stdout + result.stderr


def test_a_skip_with_no_declared_reason_fails_the_run(planted, tmp_path):
    write_test(planted, "import pytest\ndef test_skip():\n    pytest.skip('no reason that is declared')\n")
    report = tmp_path / "r.json"
    result = run_runner("--no-postgres", "--report", str(report), *pytest_args_for(planted))
    assert result.returncode == 87 and "no declared reason" in result.stderr
    assert json.loads(report.read_text())["skips_undeclared"][0]["reason"] == "no reason that is declared"


def test_a_host_listener_on_the_stub_port_is_invisible_inside_the_sandbox(planted):
    low, high = runner.ephemeral_range()
    probe = socket.socket()
    port = None
    for candidate in range(21000, 29000, 7):
        try:
            probe.bind(("127.0.0.1", candidate))
            port = candidate
            break
        except OSError:
            continue
    assert port and not low <= port <= high
    probe.listen(5)
    write_test(planted, "def test_ok():\n    assert True\n")
    try:
        result = run_runner("--no-postgres", "--stub-port", str(port), *pytest_args_for(planted))
    finally:
        probe.close()
    assert result.returncode == 0, result.stdout + result.stderr  # the stub answered with the run id, not the host listener


def test_a_host_unix_socket_outside_the_run_directory_is_unreachable_and_refused(planted, tmp_path):
    path = tmp_path / "outside.sock"
    server = socket.socket(socket.AF_UNIX)
    server.bind(str(path))
    server.listen(1)
    write_test(planted, f"""
        import os, socket, subprocess, sys
        def test_outside_socket_is_absent():
            assert not os.path.exists({str(path)!r})
            code = "import socket,sys\\ns=socket.socket(socket.AF_UNIX)\\ntry:\\n    s.connect({str(path)!r})\\nexcept OSError as e:\\n    print(e.errno)\\n"
            out = subprocess.run([sys.executable, '-c', code], env={{'PATH': os.environ['PATH']}}, capture_output=True, text=True)
            assert out.stdout.strip() == '2', out.stdout + out.stderr
    """)
    try:
        result = run_runner("--no-postgres", *pytest_args_for(planted))
    finally:
        server.close()
    assert result.returncode == 0, result.stdout + result.stderr


def test_an_unbound_interpreter_tree_exits_86(planted):
    if not runner.interpreter_trees():
        pytest.skip("the interpreter is under /usr: nothing to omit")  # declared by the canary host run
    write_test(planted, "def test_ok():\n    assert True\n")
    result = run_runner("--no-postgres", "--debug-omit-interpreter-trees", *pytest_args_for(planted))
    assert result.returncode == 86, result.stdout + result.stderr
    assert "test session starts" not in result.stdout + result.stderr


def test_a_manifest_entry_for_an_external_service_is_refused_by_the_runner(tmp_path):
    run_dir = "/tmp/dfi-00000000"
    good = runner.make_manifest(run_dir, "00000000", 21000, run_dir + "/pg/.s.PGSQL.5432")
    runner.validate_manifest(good, run_dir)
    bad_tcp = dict(good, tcp=[{"host": "203.0.113.5", "port": 5432, "service": "external"}])
    with pytest.raises(runner.Precondition):
        runner.validate_manifest(bad_tcp, run_dir)
    bad_unix = dict(good, unix=[{"path": "/var/run/postgresql/.s.PGSQL.5432", "service": "system"}])
    with pytest.raises(runner.Precondition):
        runner.validate_manifest(bad_unix, run_dir)


def test_nothing_in_the_runner_pulls_an_image():
    for name in ("scripts/isolated_test_runner.py", "tests/isolation/services.py", "scripts/run-tests-isolated.sh"):
        text = (REPO / name).read_text()
        assert '"pull"' not in text.replace('"--pull=never"', "") and "docker pull" not in text, name


def test_coverage_outputs_are_writable_while_the_repository_is_read_only(planted):
    write_test(planted, "def test_ok():\n    assert True\n")
    result = run_runner(
        "--no-postgres", "--", str(planted / "check_planted.py"), "--confcutdir", str(planted), "-c", str(REPO / "pytest.ini"),
        "--rootdir", str(REPO), "-o", "python_files=check_*.py",
        "-o", f"addopts=--cov={planted} --cov-report=term --cov-report=xml --cov-report=html")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (REPO / "coverage.xml").stat().st_size > 0 and (REPO / "htmlcov" / "index.html").exists()
