"""app/tests conftest: the same direct-pytest gate as the repository root (finding M1).

It closes `--confcutdir app/tests`, which skips the root conftest. It cannot close `--noconftest`
(see "Known limits" in doc/system/15-testing.md). Do not add imports above the gate call.
"""

import importlib.util
import os
import sys


def _load_isolation_gate():
    name = "_dataforge_isolation_gate"
    if name in sys.modules:
        return sys.modules[name]
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tests", "isolation", "gate.py")
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception:  # noqa: BLE001 - fail closed
        frame = sys._getframe()  # stop pytest's capture, or the message is lost
        while frame is not None:
            if hasattr(frame.f_locals.get("self"), "get_plugin"):
                try:
                    frame.f_locals["self"].get_plugin("capturemanager").stop_global_capturing()
                except Exception:  # noqa: BLE001
                    pass
                break
            frame = frame.f_back
        os.write(2, b"REFUSED (exit 87): the isolation gate is missing: " + path.encode() + b"\n")
        os._exit(87)
    sys.modules[name] = module
    return module


_load_isolation_gate().refuse_unless_guarded()
