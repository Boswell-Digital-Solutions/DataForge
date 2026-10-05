"""The direct-pytest gate of the isolated runner (finding M1).

Standard library only: no third-party import and no `app` import. Both the repository-root
conftest.py and tests/conftest.py call refuse_unless_guarded() before any other import, so a
run that did not start through scripts/run-tests-isolated.sh exits 87 and imports nothing of
the application. That covers tests/, app/tests/ and any later test directory under the root.
There is no override and no --collect-only exemption. A second call does the same check again.
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
