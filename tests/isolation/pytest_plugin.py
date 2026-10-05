"""Pytest plugin of the isolated runner (load it with `-p pytest_plugin`).

It checks the guard before conftest runs, turns a violation into a failed test,
skips the tests that need a declared-absent service, and records every skip.
"""

from __future__ import annotations

import inspect
import json
import os
import sys

import pytest

import netguard

EXIT_REFUSED = 87
_state = {"skips": [], "absent_skips": 0}


def _refuse(message: str, config=None) -> None:
    """Stop the run with exit 87. Stop pytest's capture first, or the message is lost."""
    try:
        config.pluginmanager.get_plugin("capturemanager").stop_global_capturing()
    except Exception:  # noqa: BLE001 - no capture is active yet at import time
        pass
    os.write(2, ("NETGUARD-REFUSED " + message + "\n").encode())
    os._exit(EXIT_REFUSED)


def early_check_reason(installed: bool, run_id, env_run_id, early_imports) -> "str | None":
    """Return the reason to refuse, or None. Pure function, so a canary can test it."""
    if not installed or not run_id or run_id != env_run_id:
        return "the guard is not installed for this run"
    if early_imports:
        return "modules were imported before the guard: " + ", ".join(early_imports)
    return None


def pytest_load_initial_conftests(early_config, parser, args):
    reason = early_check_reason(
        netguard.INSTALLED, netguard.RUN_ID, os.environ.get("NETGUARD_RUN_ID"), netguard.EARLY_IMPORTS
    )
    if reason:
        _refuse(reason, early_config)


pytest_load_initial_conftests.tryfirst = True


# The same check at import time: `-p` loads this module before pytest starts to capture output.
_reason_at_import = early_check_reason(
    netguard.INSTALLED, netguard.RUN_ID, os.environ.get("NETGUARD_RUN_ID"), netguard.EARLY_IMPORTS
)
if _reason_at_import:
    _refuse(_reason_at_import)


def _log_dir() -> str:
    return netguard.MANIFEST.get("log_dir", "")


def _declared_skip_patterns() -> list:
    return list(netguard.MANIFEST.get("declared_skip_patterns", []))


def pytest_collection_modifyitems(config, items):
    absent = netguard.MANIFEST.get("declared_absent", [])
    redis_entry = next((a for a in absent if a["service"] == "redis"), None)
    if not redis_entry:
        return
    reason = "declared absent: redis (%s)" % redis_entry["reason"]
    for item in items:
        function = getattr(item, "function", None)
        if function is None:
            continue
        try:
            source = inspect.getsource(function)
        except (OSError, TypeError):
            continue
        if "_get_redis_or_skip" in source:
            item.add_marker(pytest.mark.skip(reason=reason))
            _state["absent_skips"] += 1


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    netguard.CURRENT_TEST = item.nodeid
    os.environ["NETGUARD_CURRENT_TEST"] = item.nodeid
    item._ng_lines = netguard.violation_lines()
    yield
    netguard.CURRENT_TEST = None


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    now = netguard.violation_lines()
    before = getattr(item, "_ng_lines", now)
    if now != before:
        item._ng_lines = now
        if report.outcome != "failed":
            report.outcome = "failed"
            report.longrepr = "NetworkIsolationViolation: %d new violation(s) during %s of %s" % (
                now - before, call.when, item.nodeid)
            if hasattr(report, "wasxfail"):
                del report.wasxfail


def _skip_reason(report) -> str:
    longrepr = report.longrepr
    if isinstance(longrepr, tuple) and len(longrepr) == 3:
        text = str(longrepr[2])
    else:
        text = str(longrepr)
    return text[len("Skipped: "):] if text.startswith("Skipped: ") else text


def pytest_runtest_logreport(report):
    if report.skipped and not hasattr(report, "wasxfail"):
        reason = _skip_reason(report)
        declared = reason.startswith("declared absent:") or any(p in reason for p in _declared_skip_patterns())
        _state["skips"].append({"nodeid": report.nodeid, "reason": reason, "declared": declared})


def pytest_sessionfinish(session, exitstatus):
    log_dir = _log_dir()
    if not log_dir:
        return
    path = os.path.join(log_dir, "skips-%d.json" % os.getpid())
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(_state, handle, indent=1, sort_keys=True)
    except OSError as exc:
        _refuse("cannot write the skip report: %r" % (exc,))
