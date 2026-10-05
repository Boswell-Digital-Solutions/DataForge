"""Outside services of the isolated runner: the disposable PostgreSQL container.

The container has no network (`--network none`). Its only door is a Unix-domain socket
in a directory that the runner binds in. The runner never pulls an image. A missing
image is a precondition failure (exit 86 in the runner).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time

IMAGE = "pgvector/pgvector:pg16"
# The repository digest of the pinned image (the CI workflow pulls this digest in a separate, declared step).
IMAGE_DIGEST = "sha256:a36250871de0833b8757561c72f2477ef1ddd1101afa4e617fb552e0de514c6b"
SOCKET_NAME = ".s.PGSQL.5432"
CONTAINER_SOCKET_DIR = "/var/run/postgresql"


class ServiceError(RuntimeError):
    """A service did not start, or its identity check failed."""


_DOCKER_ENV: dict = {}


def docker_env(context: "str | None" = None, host: "str | None" = None) -> dict:
    """The explicit environment of every docker call. It has no ambient DOCKER_* variable."""
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", "/tmp")}
    if context:
        env["DOCKER_CONTEXT"] = context
    if host:
        env["DOCKER_HOST"] = host
    return env


def check_docker_local(ambient: dict) -> dict:
    """Refuse a docker client that does not talk to a local Unix socket. Return the env to use."""
    host = ambient.get("DOCKER_HOST")
    if host and not host.startswith("unix://"):
        raise ServiceError("DOCKER_HOST %r is not a local unix endpoint" % host)
    ctx_env = docker_env(host=host)
    context = ambient.get("DOCKER_CONTEXT")
    if not context:
        shown = subprocess.run(["docker", "context", "show"], capture_output=True, text=True, env=ctx_env)
        if shown.returncode != 0:
            raise ServiceError("docker context show failed: %s" % shown.stderr.strip()[:200])
        context = shown.stdout.strip()
    inspected = subprocess.run(["docker", "context", "inspect", context], capture_output=True, text=True, env=ctx_env)
    try:
        endpoint = json.loads(inspected.stdout)[0]["Endpoints"]["docker"]["Host"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise ServiceError("cannot resolve the endpoint of docker context %r" % context)
    if not endpoint.startswith("unix://") and not host:
        raise ServiceError("docker context %r points at %r, not a local unix endpoint" % (context, endpoint))
    env = docker_env(context=context, host=host)
    _DOCKER_ENV.clear()
    _DOCKER_ENV.update(env)
    return env


def _docker(*args: str, timeout: int = 120, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout,
                            env=dict(_DOCKER_ENV) or docker_env())
    if check and result.returncode != 0:
        raise ServiceError("docker %s failed: %s" % (" ".join(args[:2]), result.stderr.strip()[:400]))
    return result


def image_id(image: str = IMAGE, digest: "str | None" = IMAGE_DIGEST) -> str:
    """Return the local image id. It never pulls. It refuses an image whose digest is not the pin."""
    result = _docker("image", "inspect", "--format", "{{.Id}} {{json .RepoDigests}}", image, check=False)
    if result.returncode != 0:
        raise ServiceError("image %s is not in the local store (the runner never pulls)" % image)
    found, _, digests = result.stdout.strip().partition(" ")
    if digest and digest not in digests:
        raise ServiceError("image %s does not have the pinned digest %s (it has %s)" % (image, digest, digests))
    return found


def start_postgres(run_id: str, socket_dir: str, role: str, password: str, image: str = IMAGE,
                   fail_after_run: bool = False) -> dict:
    """Start the container and wait until the server answers on the socket. Return its record."""
    wanted = image_id(image)
    name = "dfiso-pg-%s" % run_id
    os.chmod(socket_dir, 0o777)  # the container user must create the socket here
    _docker(
        "run", "--detach", "--rm", "--pull=never", "--network", "none",
        "--name", name, "--label", "dfiso.run=%s" % run_id,
        "--security-opt", "no-new-privileges",
        "--tmpfs", "/var/lib/postgresql/data",
        "-v", "%s:%s" % (socket_dir, CONTAINER_SOCKET_DIR),
        "-e", "POSTGRES_USER=%s" % role, "-e", "POSTGRES_PASSWORD=%s" % password,
        "-e", "POSTGRES_DB=postgres",
        image,
        "postgres", "-c", "listen_addresses=", "-c", "fsync=off",
    )
    if fail_after_run:  # a canary option: force a readiness failure after the container exists
        raise ServiceError("forced failure after docker run")
    container_id = _docker("inspect", "--format", "{{.Id}}", name).stdout.strip()
    record = {
        "name": name, "container_id": container_id, "image": image, "image_id": wanted,
        "socket": os.path.join(socket_dir, SOCKET_NAME), "role": role,
    }
    deadline = time.time() + 90
    while time.time() < deadline:
        ready = _docker(
            "exec", name, "pg_isready", "-h", CONTAINER_SOCKET_DIR, "-U", role, check=False
        )
        if ready.returncode == 0 and os.path.exists(record["socket"]):
            return record
        if _docker("inspect", "--format", "{{.State.Running}}", name, check=False).stdout.strip() != "true":
            raise ServiceError("the container stopped: %s" % _docker("logs", name, check=False).stdout[-400:])
        time.sleep(1)
    raise ServiceError("the server did not answer on the socket within 90 seconds")


def psql(record: dict, sql: str, database: str = "postgres") -> str:
    result = _docker(
        "exec", record["name"], "psql", "-h", CONTAINER_SOCKET_DIR, "-U", record["role"], "-d", database,
        "-X", "-A", "-t", "-v", "ON_ERROR_STOP=1", "-c", sql,
    )
    return result.stdout.strip()


def verify_identity_outside(record: dict, run_id: str) -> dict:
    """Identity checks from outside: network mode, image, socket type, marker row."""
    info = json.loads(_docker("inspect", record["name"]).stdout)[0]
    if info["HostConfig"]["NetworkMode"] != "none":
        raise ServiceError("the container is not on --network none")
    if info["Image"] != record["image_id"] or info["Id"] != record["container_id"]:
        raise ServiceError("the container identity changed")
    mode = os.stat(record["socket"]).st_mode
    if (mode & 0o170000) != 0o140000:
        raise ServiceError("the socket path is not a socket")
    psql(record, "CREATE TABLE IF NOT EXISTS dfiso_marker (run_id text); DELETE FROM dfiso_marker;")
    psql(record, "INSERT INTO dfiso_marker VALUES ('%s');" % re.sub(r"[^0-9a-f]", "", run_id))
    version = psql(record, "SHOW server_version")
    extension = psql(record, "SELECT count(*) FROM pg_available_extensions WHERE name = 'vector'")
    return {"server_version": version, "pgvector_available": extension == "1", "socket_owner_uid": os.stat(record["socket"]).st_uid}


def create_database(record: dict, name: str) -> None:
    psql(record, 'CREATE DATABASE "%s"' % name)


def container_name(run_id: str) -> str:
    return "dfiso-pg-%s" % run_id


def remove_container(name: str, socket_dir: "str | None" = None) -> bool:
    """Stop and remove a container by name. Return True when nothing of it remains.

    The image makes the socket directory owned by uid 999 with the sticky bit, so the runner
    cannot delete the socket files itself. A graceful stop makes the server remove them.
    """
    _docker("stop", "--time", "20", name, check=False, timeout=60)
    _docker("rm", "--force", name, check=False, timeout=60)
    gone = _docker("inspect", name, check=False).returncode != 0
    if socket_dir and os.path.isdir(socket_dir) and os.listdir(socket_dir):
        # A stop during initdb can leave socket files that belong to uid 999. A throwaway container
        # of the same pinned image removes them (no network, never a pull).
        _docker("run", "--rm", "--pull=never", "--network", "none", "-v", "%s:/d" % socket_dir,
                "--entrypoint", "sh", IMAGE, "-c", "rm -f /d/.s.PGSQL.*", check=False, timeout=60)
    return gone and not (socket_dir and os.path.isdir(socket_dir) and os.listdir(socket_dir))


def stop_postgres(record: dict) -> bool:
    return remove_container(record["name"])
