#!/usr/bin/env python3
"""Closure evidence tool for finding M1: a planted violation in the real suite must fail the run.

It plants one temporary test file in tests/. The file holds two tests. One connects to 192.0.2.1
(RFC 5737). One resolves x.invalid. Each wraps the call in `except Exception: pytest.skip(...)`.
It runs only that file through the isolated runner, with the real tests/conftest.py (so `app`
loads under the guard). It expects exit 87, two failed tests and two recorded violations.
It removes the file in every case. It proves nothing about M1 by itself: closure needs the other steps.

Usage: python scripts/prove_planted_violation.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PLANTED = REPO / "tests" / "test_zz_planted_violation.py"
SOURCE = '''"""Planted by scripts/prove_planted_violation.py. It is removed after the run."""
import socket

import pytest


def test_planted_connect_to_a_documentation_address():
    try:
        socket.create_connection(("192.0.2.1", 80), timeout=1)
    except Exception as exc:  # the guard error is a BaseException, so this line must not catch it
        pytest.skip("service not available: %s" % exc)


def test_planted_lookup_of_an_invalid_name():
    try:
        socket.getaddrinfo("x.invalid", 80)
    except Exception as exc:
        pytest.skip("service not available: %s" % exc)
'''


def main() -> int:
    report = Path(tempfile.mkdtemp(prefix="planted-proof-")) / "report.json"
    PLANTED.write_text(SOURCE)
    try:
        env = dict(os.environ)
        result = subprocess.run(
            [str(REPO / "scripts" / "run-tests-isolated.sh"), "--no-postgres", "--report", str(report), "--",
             str(PLANTED.relative_to(REPO)), "-q", "-o", "addopts="],
            cwd=str(REPO), env=env, capture_output=True, text=True, timeout=600)
    finally:
        PLANTED.unlink(missing_ok=True)
    data = json.loads(report.read_text()) if report.exists() else {}
    checks = {
        "exit code is 87": result.returncode == 87,
        "two violations are recorded": data.get("violations") == 2,
        "two tests failed": "2 failed" in result.stdout,
        "no skip passed as a skip": "skipped" not in result.stdout.split("short test summary")[-1],
    }
    for name, ok in checks.items():
        print(("PASS  " if ok else "FAIL  ") + name)
    if not all(checks.values()):
        sys.stdout.write(result.stdout[-3000:] + result.stderr[-3000:])
        return 1
    print("The planted violation failed the run with exit 87 and two records in violations.jsonl.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
