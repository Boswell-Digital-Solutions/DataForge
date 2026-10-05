"""Offline tests for the private-dependency auth steps in the CI workflows.

The shell of each step is read from the workflow YAML and run with a stub `git`. No token is real,
and nothing reaches GitHub.
"""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
ACTION = ROOT / ".github" / "actions" / "private-deps-token" / "action.yml"
TEST_WORKFLOW = ROOT / ".github" / "workflows" / "test.yml"
TEL = "ghs_TEL_" + "a" * 40
CC = "ghs_CC_" + "b" * 40
LEGACY = "ghs_LEGACY_" + "c" * 40


def _step_run(path: Path, name: str) -> str:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    steps = data["runs"]["steps"] if "runs" in data else [
        s for job in data["jobs"].values() for s in job.get("steps", [])
    ]
    for step in steps:
        if step.get("name") == name:
            return step["run"]
    raise AssertionError(f"step not found: {name}")


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.log = self.root / "git.log"
        # Stub git. `ls-remote URL` succeeds only when the token in the URL may read that repository.
        stub = self.bin / "git"
        stub.write_text(
            f"""#!/usr/bin/env bash
printf '%s\\n' "$*" >> "{self.log}"
if [ "$1" = "ls-remote" ]; then
  url="$2"
  case "$url" in
    *"{TEL}@"*forge-telemetry.git) exit 0 ;;
    *"{TEL}@"*forge_contract_core.git) [ -n "${{LEAK_TEL:-}}" ] && exit 0 || exit 128 ;;
    *"{CC}@"*forge_contract_core.git) [ -z "${{CC_CANNOT_READ_OWN:-}}" ] && exit 0 || exit 128 ;;
    *"{CC}@"*forge-telemetry.git) [ -n "${{LEAK_CC:-}}" ] && exit 0 || exit 128 ;;
    *"{LEGACY}@"*) [ -z "${{LEGACY_DENIED:-}}" ] && exit 0 || exit 128 ;;
  esac
  exit 128
fi
exit 0
""",
            encoding="utf-8",
        )
        stub.chmod(stub.stat().st_mode | stat.S_IXUSR)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _bash(self, script: str, **env: str) -> subprocess.CompletedProcess[str]:
        full = os.environ.copy()
        full.update({"PATH": f"{self.bin}:{full['PATH']}", "RUNNER_TEMP": str(self.root)})
        full.update(env)
        return subprocess.run(
            ["bash", "-e", "-o", "pipefail", "-c", script],
            env=full,
            text=True,
            capture_output=True,
            check=False,
        )


class VerifyStepTests(_Base):
    script = _step_run(TEST_WORKFLOW, "Verify the minted token can actually clone")

    def _split(self, **extra: str) -> subprocess.CompletedProcess[str]:
        return self._bash(
            self.script,
            BUILD_AUTH_MODE="split",
            TELEMETRY_TOKEN=TEL,
            CONTRACT_CORE_TOKEN=CC,
            FORGE_DEPS_TOKEN="",
            **extra,
        )

    def test_split_passes_when_each_token_reaches_only_its_own_repository(self) -> None:
        result = self._split()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("each token reaches its own repository only", result.stdout)

    def test_split_fails_when_the_telemetry_token_reaches_contract_core(self) -> None:
        result = self._split(LEAK_TEL="1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("telemetry build App token can read forge_contract_core", result.stdout)

    def test_split_fails_when_the_contract_core_token_reaches_telemetry(self) -> None:
        result = self._split(LEAK_CC="1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("contract-core build App token can read forge-telemetry", result.stdout)

    def test_split_fails_when_a_token_cannot_read_its_own_repository(self) -> None:
        result = self._split(CC_CANNOT_READ_OWN="1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("contract-core build App token cannot read forge_contract_core", result.stdout)

    def test_split_never_uses_the_legacy_token(self) -> None:
        self._split()
        self.assertNotIn(LEGACY, self.log.read_text(encoding="utf-8"))

    def test_legacy_mode_keeps_its_check(self) -> None:
        ok = self._bash(
            self.script,
            BUILD_AUTH_MODE="legacy",
            FORGE_DEPS_TOKEN=LEGACY,
            TELEMETRY_TOKEN="",
            CONTRACT_CORE_TOKEN="",
        )
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        self.assertIn("forge-telemetry reachable with the minted app token", ok.stdout)
        denied = self._bash(
            self.script,
            BUILD_AUTH_MODE="legacy",
            FORGE_DEPS_TOKEN=LEGACY,
            TELEMETRY_TOKEN="",
            CONTRACT_CORE_TOKEN="",
            LEGACY_DENIED="1",
        )
        self.assertEqual(denied.returncode, 1)
        self.assertIn("cannot read forge-telemetry", denied.stdout)


class InstallStepTests(_Base):
    script = _step_run(TEST_WORKFLOW, "Install dependencies")

    def setUp(self) -> None:
        super().setUp()
        # pip must not run. Replace python with a recorder.
        py = self.bin / "python"
        py.write_text(f"#!/usr/bin/env bash\nprintf 'python %s\\n' \"$*\" >> \"{self.log}\"\n", encoding="utf-8")
        py.chmod(py.stat().st_mode | stat.S_IXUSR)

    def test_split_scopes_each_token_to_its_repository_url_and_removes_them(self) -> None:
        result = self._bash(
            self.script,
            BUILD_AUTH_MODE="split",
            TELEMETRY_TOKEN=TEL,
            CONTRACT_CORE_TOKEN=CC,
            FORGE_DEPS_TOKEN="",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        log = self.log.read_text(encoding="utf-8")
        self.assertIn(f"x-access-token:{TEL}@github.com/Boswell-Digital-Solutions/forge-telemetry.git.insteadOf", log)
        self.assertIn(f"x-access-token:{CC}@github.com/Boswell-Digital-Solutions/forge_contract_core.git.insteadOf", log)
        # No root rewrite: no token serves an unrelated github.com URL.
        self.assertNotIn("@github.com/.insteadOf", log)
        self.assertEqual(log.count("--unset"), 2)

    def test_legacy_mode_keeps_the_single_rewrite(self) -> None:
        result = self._bash(
            self.script,
            BUILD_AUTH_MODE="legacy",
            FORGE_DEPS_TOKEN=LEGACY,
            TELEMETRY_TOKEN="",
            CONTRACT_CORE_TOKEN="",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        log = self.log.read_text(encoding="utf-8")
        self.assertIn(f"url.https://x-access-token:{LEGACY}@github.com/.insteadOf", log)


class ModeStepTests(_Base):
    script = _step_run(ACTION, "Resolve and validate the mode")

    def _mode(self, mode: str, **values: str) -> tuple[subprocess.CompletedProcess[str], str]:
        out = self.root / "out"
        out.write_text("", encoding="utf-8")
        env = {
            "MODE": mode,
            "TELEMETRY_ID": "Iv.t",
            "TELEMETRY_KEY": "k1",
            "CONTRACT_ID": "Iv.c",
            "CONTRACT_KEY": "k2",
            "GITHUB_OUTPUT": str(out),
        }
        env.update(values)
        result = self._bash(self.script, **env)
        return result, out.read_text(encoding="utf-8")

    def test_empty_and_legacy_modes_resolve_to_legacy(self) -> None:
        for mode in ("", "legacy"):
            with self.subTest(mode=mode):
                result, out = self._mode(mode, TELEMETRY_ID="", TELEMETRY_KEY="", CONTRACT_ID="", CONTRACT_KEY="")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(out.strip(), "mode=legacy")

    def test_split_needs_all_four_values_and_has_no_fallback(self) -> None:
        for missing in ("TELEMETRY_ID", "TELEMETRY_KEY", "CONTRACT_ID", "CONTRACT_KEY"):
            with self.subTest(missing=missing):
                result, out = self._mode("split", **{missing: ""})
                self.assertEqual(result.returncode, 1)
                self.assertIn("No fallback credential is used", result.stdout)
                self.assertEqual(out, "")

    def test_split_with_every_value_resolves_to_split(self) -> None:
        result, out = self._mode("split")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(out.strip(), "mode=split")

    def test_an_unknown_mode_is_refused(self) -> None:
        result, out = self._mode("Split")
        self.assertEqual(result.returncode, 1)
        self.assertIn("must be legacy or split", result.stdout)
        self.assertEqual(out, "")


class WorkflowWiringTests(unittest.TestCase):
    def test_split_mode_never_reads_the_legacy_app(self) -> None:
        action = yaml.safe_load(ACTION.read_text(encoding="utf-8"))
        by_id = {s.get("id"): s for s in action["runs"]["steps"] if s.get("id")}
        self.assertEqual(by_id["legacy"]["if"], "steps.mode.outputs.mode == 'legacy'")
        self.assertEqual(by_id["telemetry"]["if"], "steps.mode.outputs.mode == 'split'")
        self.assertEqual(by_id["contract-core"]["if"], "steps.mode.outputs.mode == 'split'")
        self.assertEqual(by_id["telemetry"]["with"]["repositories"], "forge-telemetry")
        self.assertEqual(by_id["contract-core"]["with"]["repositories"], "forge_contract_core")
        self.assertEqual(by_id["telemetry"]["with"]["permission-contents"], "read")
        self.assertEqual(by_id["contract-core"]["with"]["permission-contents"], "read")
        self.assertEqual(by_id["legacy"]["with"]["repositories"], "forge-telemetry,forge_contract_core")

    def test_each_consumer_uses_the_action_and_passes_the_mode(self) -> None:
        for name in ("test.yml", "docker.yml", "deploy.yml"):
            with self.subTest(workflow=name):
                text = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
                self.assertIn("uses: ./.github/actions/private-deps-token", text)
                self.assertIn("mode: ${{ vars.FORGE_BUILD_AUTH_MODE }}", text)
                self.assertNotIn("repositories: forge-telemetry,forge_contract_core", text)

    def test_docker_workflows_pass_the_mode_and_one_secret_per_repository(self) -> None:
        for name in ("docker.yml", "deploy.yml"):
            with self.subTest(workflow=name):
                text = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
                self.assertIn("BUILD_AUTH_MODE=${{ steps.app-token.outputs.mode }}", text)
                self.assertIn("telemetry_token=${{ steps.app-token.outputs.telemetry-token }}", text)
                self.assertIn("contract_core_token=${{ steps.app-token.outputs.contract-core-token }}", text)


if __name__ == "__main__":
    unittest.main()
