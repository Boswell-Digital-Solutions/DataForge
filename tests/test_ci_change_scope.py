"""The code scans skip for a documentation-only change (standing rule, 2026-10-01).

`scripts/ci-change-scope.sh` decides. A wrong `code=false` skips the scans on a code change,
so the script fails closed: an unknown scope is code.
"""

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "ci-change-scope.sh"


def scope(paths) -> str:
    text = paths if isinstance(paths, str) else "\n".join(paths) + "\n"
    run = subprocess.run(
        ["bash", str(SCRIPT)], input=text, capture_output=True, text=True, check=False
    )
    assert run.returncode == 0, run.stderr
    return run.stdout.strip()


@pytest.mark.parametrize(
    "paths",
    [
        ["docs/KNOWN_ISSUES.md"],
        ["doc/system/15-testing.md", "doc/DTFSYSTEM.md", "docs/plans/x.md"],
        ["README.md", "CLAUDE.md", "app/api/RUNS_ROUTER_README.md"],
    ],
)
def test_a_documentation_only_change_is_not_code(paths):
    assert scope(paths) == "code=false"


@pytest.mark.parametrize(
    "paths",
    [
        ["docs/a.md", "app/main.py"],
        ["requirements.txt"],
        ["service_contract.v1.json"],
        ["src/docs.ts"],
        ["mydocs/a.py"],
        ["notes.md.bak"],
    ],
)
def test_any_other_file_makes_the_change_code(paths):
    assert scope(paths) == "code=true"


def test_a_workflow_or_a_script_change_is_code_even_beside_documentation():
    assert scope([".github/workflows/security.yml", "docs/a.md"]) == "code=true"
    assert scope(["scripts/ci-change-scope.sh", "docs/a.md"]) == "code=true"


@pytest.mark.parametrize(
    "path",
    [
        "docs/plans/DFG_GOV_01/fixtures/valid.json",
        "docs/plans/DFG_GOV_01/README.md",
        "docs/archive/TELEMETRY_INTEGRATION_STATUS.md",
    ],
)
def test_a_documentation_path_that_a_test_reads_is_code(path):
    assert scope([path]) == "code=true"


def test_an_unknown_scope_is_code():
    assert scope("") == "code=true"
    assert scope("\n\n") == "code=true"
