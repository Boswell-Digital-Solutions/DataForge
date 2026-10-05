"""Helpers of the sandbox canaries. They run inside the sandbox, under the runner.

A canary that provokes a violation runs it in a nested guarded child with its own
scratch manifest and its own violation file, so that the real record of the run
stays empty. Only RFC 5737 addresses (192.0.2.0/24) and `.invalid` names appear here.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

DOC_ADDRESS = "192.0.2.1"  # RFC 5737 TEST-NET-1: never routed
INVALID_NAME = "canary.invalid"
GUARD_DIR = os.environ["NETGUARD_GUARD_DIR"]
REPO = Path(__file__).resolve().parents[4]
BASE_ENV = {"PATH": os.environ["PATH"], "HOME": "/tmp", "LANG": "C.UTF-8", "TMPDIR": "/tmp"}


def write_manifest(tmp: Path, tcp=(), unix=(), absent=(), programs=("python*", "bash", "sh", "git", "openssl"), violations=None) -> dict:
    run_id = "nested-" + uuid.uuid4().hex[:8]
    log_dir = tmp / "log"
    log_dir.mkdir(exist_ok=True)
    manifest = {
        "version": 1, "run_id": run_id,
        "violations_path": str(violations or tmp / "violations.jsonl"),
        "declared_absent_log": str(tmp / "absent.jsonl"),
        "log_dir": str(log_dir),
        "tcp": [{"host": "127.0.0.1", "port": p, "service": "canary"} for p in tcp],
        "unix": [{"path": u, "service": "canary"} for u in unix],
        "declared_absent": [{"service": "redis", "path": a, "reason": "canary"} for a in absent],
        "programs": list(programs), "declared_skip_patterns": [],
    }
    path = tmp / "manifest.json"
    path.write_text(json.dumps(manifest))
    env = dict(BASE_ENV)
    env.update(PYTHONPATH=GUARD_DIR, NETGUARD_RUN_ID=run_id, NETGUARD_MANIFEST=str(path))
    return {"env": env, "manifest": manifest, "violations": Path(manifest["violations_path"]), "absent": Path(manifest["declared_absent_log"])}


def lines(path: Path) -> list:
    try:
        return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    except OSError:
        return []


def run_guarded(tmp: Path, code: str, timeout=60, env_extra=None, **manifest_kwargs):
    nested = write_manifest(tmp, **manifest_kwargs)
    env = nested["env"]
    env.update(env_extra or {})
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=timeout, cwd=str(tmp))
    return result, nested


def run_unguarded(code: str, timeout=30):
    """A child with no guard and no PYTHONPATH: only the namespaces protect it."""
    return subprocess.run([sys.executable, "-c", code], env=dict(BASE_ENV), capture_output=True, text=True, timeout=timeout)
