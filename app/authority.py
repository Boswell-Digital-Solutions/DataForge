"""This service's self-reported authority domain (FC-LTA-P006).

Forge_Command's Living Topology V2 needs machine-readable evidence of what
authority domain this service self-reports, to compare against its own
approved intended governance reference. The claim itself is not new --
`doc/system/40_governance/11-scope.md` already states DataForge is "the
durable-truth boundary for the Forge ecosystem" -- only its runtime
visibility is.

This is evidence, not authority: Forge_Command's own `service_contract.v1.json`
decides whether the claim is approved. A self-declaration is never sufficient
on its own.
"""

from __future__ import annotations

import json
from pathlib import Path

_OWN_SERVICE_CONTRACT_PATH = Path(__file__).resolve().parent.parent / "service_contract.v1.json"


def load_own_authority_domain(manifest_path: Path = _OWN_SERVICE_CONTRACT_PATH) -> str | None:
    """Read this service's own declared `authority_domain` self-report.

    Never raises: a missing or malformed contract file yields `None`, not an
    error, since a self-report absent is honest, not a health failure.
    """
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    domain = manifest.get("authority_domain")
    return domain if isinstance(domain, str) and domain else None


OWN_AUTHORITY_DOMAIN = load_own_authority_domain()
