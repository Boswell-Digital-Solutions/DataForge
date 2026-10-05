"""Layer 2 (the guard) and layer 4 (visibility). Violations run in nested guarded children."""

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from canary_support import DOC_ADDRESS, GUARD_DIR, INVALID_NAME, REPO, lines, run_guarded, write_manifest

pytestmark = pytest.mark.isolation_canary

MANIFEST = json.load(open(os.environ["NETGUARD_MANIFEST"]))


def kinds(nested) -> list:
    return [v["kind"] for v in lines(nested["violations"])]


def test_the_guard_was_installed_before_pytest_and_the_modules_that_matter():
    sys.path.insert(0, GUARD_DIR)
    import netguard

    assert netguard.INSTALLED and netguard.RUN_ID == os.environ["NETGUARD_RUN_ID"]
    snapshot = json.load(open(os.path.join(MANIFEST["log_dir"], "snapshot-%d.json" % os.getpid())))
    assert snapshot["early_imports"] == []


def test_a_name_lookup_is_a_violation(tmp_path):
    result, nested = run_guarded(tmp_path, f"import socket\nsocket.getaddrinfo('{INVALID_NAME}', 80)\n")
    assert result.returncode != 0 and "NetworkIsolationViolation" in result.stderr
    assert any("name lookup" in k for k in kinds(nested))


def test_documentation_address_connect_is_a_violation(tmp_path):
    result, nested = run_guarded(tmp_path, f"import socket\nsocket.create_connection(('{DOC_ADDRESS}', 80), timeout=1)\n")
    assert result.returncode != 0
    assert any("name lookup not allowed" in k for k in kinds(nested))  # create_connection resolves first
    (tmp_path / "raw").mkdir()
    result, nested = run_guarded(tmp_path / "raw", f"import socket\ns = socket.socket()\ns.connect(('{DOC_ADDRESS}', 80))\n")
    assert result.returncode != 0 and any("host is not loopback" in k for k in kinds(nested))


def test_a_loopback_port_that_is_not_in_the_manifest_is_refused(tmp_path):
    result, nested = run_guarded(tmp_path, "import socket\nsocket.create_connection(('127.0.0.1', 5432), timeout=1)\n", tcp=[9])
    assert result.returncode != 0 and any("loopback port not in the manifest" in k for k in kinds(nested))


def test_an_allowlisted_loopback_port_is_allowed(tmp_path):
    code = textwrap.dedent(f"""
        import socket, os
        s = socket.create_connection(('127.0.0.1', {MANIFEST['tcp'][0]['port']}), timeout=3); s.close(); print('connected')
    """)
    result, nested = run_guarded(tmp_path, code, tcp=[MANIFEST["tcp"][0]["port"]])
    assert "connected" in result.stdout and kinds(nested) == []


def test_a_python_child_writes_a_violation_for_the_whole_run(tmp_path):
    code = textwrap.dedent(f"""
        import subprocess, sys
        r = subprocess.run([sys.executable, '-c', "import socket; socket.create_connection(('{DOC_ADDRESS}', 80), timeout=1)"])
        print('child rc', r.returncode)
    """)
    result, nested = run_guarded(tmp_path, code)
    assert "child rc 1" in result.stdout
    records = lines(nested["violations"])
    assert len(records) == 1 and records[0]["pid"] != 0


def test_a_spawn_of_a_program_outside_the_manifest_is_a_violation(tmp_path):
    result, nested = run_guarded(tmp_path, "import subprocess\nsubprocess.run(['/usr/bin/ls', '/'])\n")
    assert result.returncode != 0 and any("spawn of a program" in k for k in kinds(nested))
    result, nested = run_guarded(tmp_path / "x" if (tmp_path / "x").mkdir() is None else tmp_path, "import os\nos.system('true')\n")
    assert any("os.system" in k for k in kinds(nested))


def test_libpq_targets_are_checked_before_libpq_runs(tmp_path):
    pytest.importorskip("psycopg2")
    code = textwrap.dedent(f"""
        import psycopg2
        for kwargs in ({{'host': '{DOC_ADDRESS}'}}, {{}}, {{'host': '/var/run/postgresql'}}, {{'host': '127.0.0.1', 'port': 5432}},
                       {{'host': '/tmp', 'hostaddr': '{DOC_ADDRESS}'}}, {{'service': 'x', 'host': '/tmp'}}):
            try:
                psycopg2.connect(connect_timeout=1, **kwargs)
            except BaseException as e:
                print(type(e).__name__)
        try:
            psycopg2.connect('postgresql://u:p@{DOC_ADDRESS}/db', connect_timeout=1)
        except BaseException as e:
            print(type(e).__name__)
    """)
    result, nested = run_guarded(tmp_path, code)
    assert result.stdout.split().count("NetworkIsolationViolation") == 7, result.stdout + result.stderr
    assert len(lines(nested["violations"])) == 7


def test_a_redirect_to_a_hosted_name_fails_at_the_second_hop_for_httpx_and_requests(tmp_path):
    pytest.importorskip("httpx")
    pytest.importorskip("requests")
    code = textwrap.dedent("""
        import http.server, threading, socket
        hits = []
        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                hits.append(self.path)
                self.send_response(302); self.send_header('Location', 'http://hosted.invalid/'); self.send_header('Content-Length', '0'); self.end_headers()
            def log_message(self, *a): pass
        srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), H)
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        import httpx, requests
        for name, call in (('httpx', lambda: httpx.get(f'http://127.0.0.1:{port}/', follow_redirects=True)),
                           ('requests', lambda: requests.get(f'http://127.0.0.1:{port}/', allow_redirects=True))):
            try:
                call()
                print(name, 'NO-ERROR')
            except BaseException as e:
                print(name, type(e).__name__)
        print('hits', len(hits))
    """)
    result, nested = run_guarded(tmp_path, code)
    assert "httpx NetworkIsolationViolation" in result.stdout and "requests NetworkIsolationViolation" in result.stdout, result.stdout + result.stderr
    assert "hits 2" in result.stdout
    assert len(lines(nested["violations"])) == 2


def test_a_proxy_variable_stops_the_process(tmp_path):
    result, nested = run_guarded(tmp_path, "print('started')", env_extra={"HTTP_PROXY": "http://127.0.0.1:9"})
    assert "started" not in result.stdout and any("proxy" in k for k in kinds(nested))


def test_a_swallowed_violation_is_still_recorded(tmp_path):
    code = textwrap.dedent(f"""
        import socket
        try:
            socket.create_connection(('{DOC_ADDRESS}', 80), timeout=1)
        except Exception:
            print('swallowed-by-except-Exception')
    """)
    result, nested = run_guarded(tmp_path, code)
    assert "swallowed-by-except-Exception" not in result.stdout and result.returncode != 0
    assert len(lines(nested["violations"])) == 1
    code = textwrap.dedent(f"""
        import socket
        try:
            socket.create_connection(('{DOC_ADDRESS}', 80), timeout=1)
        except BaseException:
            print('swallowed-by-except-BaseException')
    """)
    (tmp_path / "b").mkdir()
    result, nested = run_guarded(tmp_path / "b", code)
    assert "swallowed-by-except-BaseException" in result.stdout and result.returncode == 0
    assert len(lines(nested["violations"])) == 1  # the record survives, so the outer runner fails the run


def test_abstract_unix_addresses_and_foreign_paths_are_refused(tmp_path):
    code = textwrap.dedent("""
        import socket
        for addr in ('\\0abstract', b'\\0abstract', '', '/var/run/docker.sock', '/tmp/not-in-manifest.sock'):
            s = socket.socket(socket.AF_UNIX)
            try:
                s.connect(addr)
            except BaseException as e:
                print(type(e).__name__)
            s.close()
        s = socket.socket(socket.AF_UNIX)
        try:
            s.bind('\\0abstract')
        except BaseException as e:
            print('bind', type(e).__name__)
    """)
    result, nested = run_guarded(tmp_path, code)
    assert result.stdout.split().count("NetworkIsolationViolation") == 6, result.stdout + result.stderr


def test_guard_rule_for_other_socket_families(tmp_path):
    code = "import socket\nfor f in (40, 16, 17):\n    try:\n        socket.socket(f, socket.SOCK_RAW if f == 17 else socket.SOCK_STREAM)\n    except BaseException as e:\n        print(f, type(e).__name__)\n"
    result, nested = run_guarded(tmp_path, code)
    names = result.stdout.split()
    assert names.count("NetworkIsolationViolation") == 3, result.stdout + result.stderr


def test_a_bind_to_a_non_loopback_address_is_refused(tmp_path):
    result, nested = run_guarded(tmp_path, "import socket\ns = socket.socket()\ns.bind(('0.0.0.0', 0))\n")
    assert result.returncode != 0 and any("host is not loopback" in k for k in kinds(nested))


def test_an_unwritable_violation_record_stops_the_process(tmp_path):
    result, _ = run_guarded(tmp_path, "print('started')", violations="/usr/cannot-write.jsonl")
    assert result.returncode == 87 and "started" not in result.stdout and "NETGUARD-FATAL" in result.stderr


def test_a_declared_absent_probe_is_logged_and_not_a_violation(tmp_path):
    absent = str(tmp_path / "redis-absent.sock")
    code = f"import socket\ns = socket.socket(socket.AF_UNIX)\ntry:\n    s.connect('{absent}')\nexcept FileNotFoundError:\n    print('absent')\n"
    result, nested = run_guarded(tmp_path, code, absent=[absent])
    assert "absent" in result.stdout and kinds(nested) == [] and len(lines(nested["absent"])) == 1


# ---- the pytest plugin, in nested pytest runs ------------------------------------------------

def nested_pytest(tmp_path, test_source, extra_env=None, **manifest_kwargs):
    nested = write_manifest(tmp_path, **manifest_kwargs)
    (tmp_path / "check_nested.py").write_text(textwrap.dedent(test_source))
    (tmp_path / "pytest.ini").write_text("[pytest]\npython_files = check_*.py\n")
    env = nested["env"]
    env.update(extra_env or {})
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "pytest_plugin", "-p", "no:cacheprovider", "-c", str(tmp_path / "pytest.ini"),
         "--rootdir", str(tmp_path), "-q", str(tmp_path / "check_nested.py")],
        env=env, capture_output=True, text=True, timeout=120, cwd=str(tmp_path))
    return result, nested


def test_a_swallowed_violation_in_a_test_is_reported_failed_not_skipped(tmp_path):
    result, nested = nested_pytest(tmp_path, f"""
        import socket, pytest
        def test_swallow():
            try:
                socket.create_connection(('{DOC_ADDRESS}', 80), timeout=1)
            except Exception as e:
                pytest.skip(f'service not available: {{e}}')
        def test_control():
            assert True
    """)
    assert result.returncode == 1 and "1 failed, 1 passed" in result.stdout, result.stdout + result.stderr
    assert len(lines(nested["violations"])) == 1  # BaseException passed the except Exception


def test_an_except_baseexception_test_is_converted_to_failed_by_the_plugin(tmp_path):
    result, nested = nested_pytest(tmp_path, f"""
        import socket
        def test_swallow_all():
            try:
                socket.create_connection(('{DOC_ADDRESS}', 80), timeout=1)
            except BaseException:
                pass
    """)
    assert result.returncode == 1 and "1 failed" in result.stdout, result.stdout
    assert len(lines(nested["violations"])) == 1


def test_declared_absent_tests_skip_before_any_connection_and_every_skip_is_enumerated(tmp_path):
    absent = str(tmp_path / "redis-absent.sock")
    helper = "_get_redis_" + "or_skip"  # the outer plugin matches this name in test source, so the literal must not appear here
    result, nested = nested_pytest(tmp_path, f"""
        import pytest
        async def {helper}():
            raise AssertionError('must not run')
        async def test_uses_redis():
            await {helper}()
        def test_plain_skip():
            pytest.skip('some other reason')
    """, absent=[absent])
    report = json.loads(next((tmp_path / "log").glob("skips-*.json")).read_text())
    by_name = {s["nodeid"].split("::")[-1]: s for s in report["skips"]}
    assert by_name["test_uses_redis"]["declared"] is True and by_name["test_uses_redis"]["reason"].startswith("declared absent: redis")
    assert by_name["test_plain_skip"]["declared"] is False
    assert lines(nested["absent"]) == []  # skipped before any connection


def test_the_plugin_refuses_imports_that_happened_before_the_guard(tmp_path):
    fake = tmp_path / "fake"
    fake.mkdir()
    (fake / "sitecustomize.py").write_text(f"import httpx\nexec(open({str(Path(GUARD_DIR) / 'sitecustomize.py')!r}).read())\n")
    nested = write_manifest(tmp_path)
    nested["env"]["PYTHONPATH"] = f"{fake}:{GUARD_DIR}"
    (tmp_path / "pytest.ini").write_text("[pytest]\n")
    result = subprocess.run([sys.executable, "-m", "pytest", "-p", "pytest_plugin", "-p", "no:cacheprovider", "-c", str(tmp_path / "pytest.ini"),
                             "--rootdir", str(tmp_path), "--collect-only", "-q"], env=nested["env"], capture_output=True, text=True, timeout=60, cwd=str(tmp_path))
    assert result.returncode == 87 and "modules were imported before the guard" in result.stderr and "httpx" in result.stderr


def test_early_check_reason_is_a_pure_decision():
    sys.path.insert(0, GUARD_DIR)
    import pytest_plugin

    assert pytest_plugin.early_check_reason(True, "a", "a", []) is None
    assert "not installed" in pytest_plugin.early_check_reason(False, None, "a", [])
    assert "not installed" in pytest_plugin.early_check_reason(True, "a", "b", [])
    assert "httpx" in pytest_plugin.early_check_reason(True, "a", "a", ["httpx"])


def test_exec_and_spawn_events_of_unlisted_programs_are_violations(tmp_path):
    code = textwrap.dedent("""
        import os
        for call in (lambda: os.posix_spawn('/usr/bin/ls', ['ls'], {}),
                     lambda: os.spawnv(os.P_WAIT, '/usr/bin/ls', ['ls']),
                     lambda: os.execv('/usr/bin/ls', ['ls'])):
            try:
                call()
            except BaseException as e:
                print(type(e).__name__)
    """)
    result, nested = run_guarded(tmp_path, code)
    # os.spawnv forks first, so its violation is raised and recorded in the forked child (3 records, 2 raises here)
    assert result.stdout.split().count("NetworkIsolationViolation") == 2, result.stdout + result.stderr
    assert len(kinds(nested)) == 3 and all("spawn of a program" in k for k in kinds(nested))


def test_the_guard_refuses_a_manifest_entry_that_is_not_a_loopback_service(tmp_path):
    nested = write_manifest(tmp_path)
    manifest = json.loads(Path(nested["env"]["NETGUARD_MANIFEST"]).read_text())
    manifest["tcp"] = [{"host": "203.0.113.5", "port": 5432, "service": "external-database"}]
    Path(nested["env"]["NETGUARD_MANIFEST"]).write_text(json.dumps(manifest))
    result = subprocess.run([sys.executable, "-c", "print('started')"], env=nested["env"], capture_output=True, text=True, cwd=str(tmp_path))
    assert result.returncode == 87 and "started" not in result.stdout and "not a loopback service" in result.stderr


def test_redis_clients_probing_the_declared_absent_path_are_logged_not_failed(tmp_path):
    pytest.importorskip("redis")
    absent = str(tmp_path / "redis-absent.sock")
    code = textwrap.dedent(f"""
        import asyncio, redis, redis.asyncio
        try:
            redis.from_url('unix://{absent}').ping()
        except Exception as e:
            print('sync', type(e).__name__)
        async def go():
            c = redis.asyncio.from_url('unix://{absent}')
            try:
                await c.ping()
            except Exception as e:
                print('async', type(e).__name__)
            await c.aclose()
        asyncio.run(go())
    """)
    result, nested = run_guarded(tmp_path, code, absent=[absent])
    assert "sync ConnectionError" in result.stdout and "async ConnectionError" in result.stdout, result.stdout + result.stderr
    assert kinds(nested) == [] and len(lines(nested["absent"])) >= 2


def test_an_inherited_socket_descriptor_stops_a_guarded_process(tmp_path):
    import socket

    left, right = socket.socketpair()
    try:
        nested = write_manifest(tmp_path)
        result = subprocess.run([sys.executable, "-c", "print('started')"], env=nested["env"], capture_output=True, text=True,
                                pass_fds=(right.fileno(),), cwd=str(tmp_path))
    finally:
        left.close()
        right.close()
    assert result.returncode == 87 and "started" not in result.stdout and "inherited descriptors" in result.stderr


def test_hostaddr_is_refused_even_with_a_manifest_socket_directory(tmp_path):
    pytest.importorskip("psycopg2")
    sock_dir = tmp_path / "pg"
    sock_dir.mkdir()
    code = textwrap.dedent(f"""
        import psycopg2
        try:
            psycopg2.connect(host={str(sock_dir)!r}, hostaddr='{DOC_ADDRESS}', user='u', dbname='d', connect_timeout=1)
        except BaseException as e:
            print(type(e).__name__, e)
    """)
    result, nested = run_guarded(tmp_path, code, unix=[str(sock_dir / ".s.PGSQL.5432")])
    assert "NetworkIsolationViolation" in result.stdout and "hostaddr" in result.stdout, result.stdout + result.stderr
    assert any("hostaddr" in k for k in kinds(nested))


def test_a_declared_skip_needs_an_exact_full_string_match(tmp_path):
    nested = write_manifest(tmp_path)
    manifest = json.loads(Path(nested["env"]["NETGUARD_MANIFEST"]).read_text())
    manifest["declared_skip_reasons"] = ["exact reason"]
    Path(nested["env"]["NETGUARD_MANIFEST"]).write_text(json.dumps(manifest))
    (tmp_path / "check_nested.py").write_text(textwrap.dedent("""
        import pytest
        def test_exact():
            pytest.skip('exact reason')
        def test_longer():
            pytest.skip('exact reason and more')
        def test_prefix():
            pytest.skip('exact')
    """))
    (tmp_path / "pytest.ini").write_text("[pytest]\npython_files = check_*.py\n")
    subprocess.run([sys.executable, "-m", "pytest", "-p", "pytest_plugin", "-p", "no:cacheprovider", "-c", str(tmp_path / "pytest.ini"),
                    "--rootdir", str(tmp_path), "-q", str(tmp_path / "check_nested.py")], env=nested["env"], capture_output=True, text=True, cwd=str(tmp_path))
    report = json.loads(next((tmp_path / "log").glob("skips-*.json")).read_text())
    declared = {s["nodeid"].split("::")[-1]: s["declared"] for s in report["skips"]}
    assert declared == {"test_exact": True, "test_longer": False, "test_prefix": False}
