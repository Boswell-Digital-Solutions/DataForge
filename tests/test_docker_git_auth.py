from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "docker-git-auth.sh"
TEL_TOKEN = "ghs_TELEMETRY_" + ("a" * 200)
CC_TOKEN = "ghs_CONTRACT_" + ("b" * 200)
LEGACY_TOKEN = "ghs_LEGACY_CANARY_" + ("c" * 50)
TEL_URL = "https://github.com/Boswell-Digital-Solutions/forge-telemetry.git@abc123"
CC_URL = "https://github.com/Boswell-Digital-Solutions/forge_contract_core.git@abc123"
OTHER_URL = "https://github.com/Boswell-Digital-Solutions/other-private.git"


class DockerGitAuthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.secrets = self.root / "secrets"
        self.secrets.mkdir()
        self.home = self.root / "home"
        self.home.mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _secret(self, name: str, value: str) -> None:
        (self.secrets / name).write_text(value, encoding="utf-8")

    def _run(self, mode: str | None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(self.home),
                "GIT_CONFIG_GLOBAL": str(self.home / ".gitconfig"),
                "DOCKER_SECRETS_DIR": str(self.secrets),
            }
        )
        env.pop("BUILD_AUTH_MODE", None)
        if mode is not None:
            env["BUILD_AUTH_MODE"] = mode
        return subprocess.run(
            ["sh", str(SCRIPT)], env=env, text=True, capture_output=True, check=False
        )

    def _rewrite(self, url: str) -> str:
        """The URL that Git would actually use for `url`, after insteadOf rewriting."""
        env = os.environ.copy()
        env.update({"HOME": str(self.home), "GIT_CONFIG_GLOBAL": str(self.home / ".gitconfig")})
        result = subprocess.run(
            ["git", "ls-remote", "--get-url", url],
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout.strip()

    def _gitconfig(self) -> str:
        path = self.home / ".gitconfig"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def test_split_mode_scopes_each_token_to_its_own_repository(self) -> None:
        self._secret("telemetry_token", TEL_TOKEN)
        self._secret("contract_core_token", CC_TOKEN)
        # A legacy secret is present on purpose. Split mode must not read it.
        self._secret("github_token", LEGACY_TOKEN)

        result = self._run("split")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"x-access-token:{TEL_TOKEN}@", self._rewrite(TEL_URL))
        self.assertIn(f"x-access-token:{CC_TOKEN}@", self._rewrite(CC_URL))
        self.assertNotIn(CC_TOKEN, self._rewrite(TEL_URL))
        self.assertNotIn(TEL_TOKEN, self._rewrite(CC_URL))
        # No other repository, and no other URL on github.com, gets a token.
        self.assertEqual(self._rewrite(OTHER_URL), OTHER_URL)
        self.assertNotIn(LEGACY_TOKEN, self._gitconfig())
        self.assertNotIn(TEL_TOKEN + CC_TOKEN, result.stdout + result.stderr)
        for token in (TEL_TOKEN, CC_TOKEN, LEGACY_TOKEN):
            self.assertNotIn(token, result.stdout + result.stderr)

    def test_split_mode_fails_closed_when_a_secret_is_missing_or_empty(self) -> None:
        for present in ("telemetry_token", "contract_core_token"):
            with self.subTest(present_only=present):
                for path in self.secrets.iterdir():
                    path.unlink()
                (self.home / ".gitconfig").unlink(missing_ok=True)
                self._secret(present, TEL_TOKEN)
                self._secret("github_token", LEGACY_TOKEN)

                result = self._run("split")

                self.assertEqual(result.returncode, 1)
                self.assertIn("No fallback credential is used", result.stderr)
                self.assertNotIn(LEGACY_TOKEN, self._gitconfig())
                self.assertNotIn(LEGACY_TOKEN, result.stdout + result.stderr)

    def test_split_mode_refuses_an_empty_secret_file(self) -> None:
        self._secret("telemetry_token", TEL_TOKEN)
        self._secret("contract_core_token", "")
        result = self._run("split")
        self.assertEqual(result.returncode, 1)
        self.assertIn("contract_core_token", result.stderr)

    def test_legacy_mode_keeps_the_single_token_behavior(self) -> None:
        self._secret("github_token", LEGACY_TOKEN)
        for mode in ("legacy", None):
            with self.subTest(mode=mode):
                (self.home / ".gitconfig").unlink(missing_ok=True)
                result = self._run(mode)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"x-access-token:{LEGACY_TOKEN}@", self._rewrite(TEL_URL))
                self.assertIn(f"x-access-token:{LEGACY_TOKEN}@", self._rewrite(CC_URL))

    def test_legacy_mode_without_a_secret_is_a_no_op(self) -> None:
        result = self._run("legacy")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self._rewrite(TEL_URL), TEL_URL)

    def test_unknown_mode_is_refused(self) -> None:
        result = self._run("Split")
        self.assertEqual(result.returncode, 1)
        self.assertIn("must be 'legacy' or 'split'", result.stderr)


if __name__ == "__main__":
    unittest.main()
