"""The explicitly identified local services: the stub and the disposable PostgreSQL."""

import http.client
import json
import os
import stat

import pytest

pytestmark = pytest.mark.isolation_canary

MANIFEST = json.load(open(os.environ["NETGUARD_MANIFEST"]))
STUB_PORT = MANIFEST["tcp"][0]["port"]


def test_stub_answers_with_the_run_identifier_and_embeds():
    conn = http.client.HTTPConnection("127.0.0.1", STUB_PORT, timeout=5)
    conn.request("GET", "/health")
    body = json.loads(conn.getresponse().read())
    assert body == {"service": "neuroforge-stub", "run_id": MANIFEST["run_id"]}
    conn.request("POST", "/api/v1/embed", body=json.dumps({"texts": ["a", "b", "c"]}), headers={"Content-Type": "application/json"})
    data = json.loads(conn.getresponse().read())
    assert len(data["embeddings"]) == 3 and all(len(v) == 1536 for v in data["embeddings"])
    conn.close()


def test_stub_port_is_outside_the_ephemeral_range():
    low, high = (int(x) for x in open("/proc/sys/net/ipv4/ip_local_port_range").read().split())
    assert not low <= STUB_PORT <= high


def test_postgres_answers_over_the_bound_socket():
    psycopg2 = pytest.importorskip("psycopg2")
    url = os.environ["DATAFORGE_RLS_TEST_POSTGRES_URL"]
    assert url, "the runner did not provide the disposable PostgreSQL"
    entry = MANIFEST["unix"][0]
    assert stat.S_ISSOCK(os.stat(entry["path"]).st_mode)
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SELECT run_id FROM dfiso_marker")
    assert cur.fetchone()[0] == MANIFEST["run_id"]
    cur.execute("SELECT current_user, version()")
    user, version = cur.fetchone()
    assert user == "dftest" and "PostgreSQL 16" in version
    conn.rollback()
    conn.autocommit = True
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cur.execute("SELECT '[1,2,3]'::vector <-> '[1,2,4]'::vector")
    assert cur.fetchone()[0] == 1.0
    conn.close()
    print("socket owner uid seen in the sandbox:", os.stat(entry["path"]).st_uid)


def test_the_runner_urls_name_the_manifest_socket_explicitly():
    url = os.environ["DATAFORGE_RLS_TEST_POSTGRES_URL"]
    assert "host=" + os.path.dirname(MANIFEST["unix"][0]["path"]) in url and "dftest@" in url and "dftest:" not in url


def test_declared_absent_probe_is_logged_and_does_not_fail_the_run():
    import socket

    absent = MANIFEST["declared_absent"][0]
    before = sum(1 for _ in open(MANIFEST["declared_absent_log"]))
    s = socket.socket(socket.AF_UNIX)
    with pytest.raises(FileNotFoundError):
        s.connect(absent["path"])
    s.close()
    after = [json.loads(x) for x in open(MANIFEST["declared_absent_log"])]
    assert len(after) == before + 1 and after[-1]["service"] == "redis" and after[-1]["kind"] == "declared-absent probe"
    assert sum(1 for _ in open(MANIFEST["violations_path"])) == 0


def test_httpx_posts_to_the_stub_like_the_application_does():
    import asyncio

    httpx = pytest.importorskip("httpx")

    async def call():
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(os.environ["NEUROFORGE_URL"] + "/api/v1/embed", json={"texts": ["test text"]})
        return response

    response = asyncio.run(call())
    assert response.status_code == 200 and len(response.json()["embeddings"][0]) == 1536


def _load_rls_module():
    """Load the RLS test module by path. It imports pytest and sqlalchemy only, never `app`."""
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[4] / "tests" / "test_security" / "test_rls_public_tables.py"
    spec = importlib.util.spec_from_file_location("rls_module_for_canary", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert "app" not in __import__("sys").modules
    return module


def test_the_rls_helpers_create_and_drop_a_database_on_the_disposable_server_only():
    import sqlalchemy as sa

    rls = _load_rls_module()
    admin = sa.engine.make_url(os.environ["DATAFORGE_RLS_TEST_POSTGRES_URL"])
    name, url = rls._create_database(admin, "canary_rls")
    try:
        engine = sa.create_engine(url)
        with engine.connect() as conn:
            assert conn.execute(sa.text("SELECT current_database()")).scalar() == name
        engine.dispose()
    finally:
        rls._drop_database(admin, name)
    for bad in ("postgresql://postgres@/postgres?host=/var/run/postgresql", "postgresql://postgres@192.0.2.1/postgres",
                "postgresql://postgres@127.0.0.1:5432/postgres", "postgresql://dftest@/postgres?host=/tmp"):
        with pytest.raises(AssertionError):
            rls._assert_disposable_host(sa.engine.make_url(bad))


def test_the_rls_alembic_child_environment_is_sanitized(monkeypatch):
    import sqlalchemy as sa

    rls = _load_rls_module()
    monkeypatch.setenv("PGHOST", "x")
    monkeypatch.setenv("DOCKER_HOST", "x")
    monkeypatch.setenv("SSH_AUTH_SOCK", "x")
    monkeypatch.setenv("HTTP_PROXY", "x")
    env = rls._child_env(sa.engine.make_url("postgresql://u:p@/db?host=/x"))
    assert not {"PGHOST", "DOCKER_HOST", "SSH_AUTH_SOCK", "HTTP_PROXY"} & set(env)
    assert env["DATAFORGE_DATABASE_URL"].endswith("host=%2Fx") and env["NETGUARD_RUN_ID"] == os.environ["NETGUARD_RUN_ID"]
