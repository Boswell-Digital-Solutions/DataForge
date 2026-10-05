"""Interpreter-start bootstrap of the network guard.

Python imports this file at start, before the test modules. It needs the runner's
NETGUARD_RUN_ID. Without it, it does nothing, and the conftest gate refuses the run.
"""

import os

if os.environ.get("NETGUARD_RUN_ID"):
    try:
        import netguard

        netguard.install()
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - a guard that cannot load must stop the process
        os.write(2, ("NETGUARD-FATAL guard did not install: %r\n" % (exc,)).encode())
        os._exit(87)
