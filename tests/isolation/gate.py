"""The direct-pytest gate of the isolated runner (finding M1).

Standard library only: no third-party import and no `app` import. The repository-root
conftest.py, tests/conftest.py and app/tests/conftest.py call refuse_unless_guarded() before any
other import. An ACCIDENTAL direct pytest run (including --collect-only) therefore exits 87 and
imports nothing of the application. There is no override flag. A second call does the same check.

It is not a barrier against a deliberate bypass. pytest --noconftest, a --confcutdir below the
root conftest outside app/tests and tests, a -p plugin that imports app, PYTEST_ADDOPTS carrying
those options, python -m unittest and plain python <file> all skip it. A hand-built install of
the netguard module with a matching NETGUARD_RUN_ID also satisfies the check. The kernel layers
of the runner are the barrier (doc/system/15-testing.md, "Threat model" and "Known limits").
"""

import os
import sys

EXIT_REFUSED = 87
MESSAGE = (
    b"REFUSED (exit 87): the network guard is not installed. "
    b"Run the suite with scripts/run-tests-isolated.sh. "
    b"See docs/proposals/M1_TEST_ISOLATION_REPAIR_DESIGN.md.\n"
)


def guarded() -> bool:
    """True only when the runner set NETGUARD_RUN_ID and the guard of that run is installed."""
    guard = sys.modules.get("netguard")
    run_id = os.environ.get("NETGUARD_RUN_ID")
    return bool(run_id) and guard is not None and getattr(guard, "INSTALLED", False) and getattr(guard, "RUN_ID", None) == run_id


def refuse_unless_guarded() -> None:
    if guarded():
        return
    # pytest captures output while it imports a conftest, and os._exit would lose the message.
    # Stop the capture through the plugin manager that is importing the conftest.
    frame = sys._getframe()
    while frame is not None:
        manager = frame.f_locals.get("self")
        if hasattr(manager, "get_plugin"):
            try:
                manager.get_plugin("capturemanager").stop_global_capturing()
            except Exception:  # noqa: BLE001 - the exit code is the contract, the message is a help
                pass
            break
        frame = frame.f_back
    os.write(2, MESSAGE)
    os._exit(EXIT_REFUSED)
