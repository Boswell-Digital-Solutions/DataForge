from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "render-git-auth.sh"
STATELESS_TOKEN = "ghs_" + ("a" * 260) + "." + ("b" * 260) + ".sig"
PRIVATE_REPOS = ("forge-telemetry", "forge_contract_core")


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _fake_tools(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    git_log = tmp_path / "git.log"
    curl_log = tmp_path / "curl.log"
    credential_log = tmp_path / "credential.log"

    _write_executable(
        bin_dir / "openssl",
        """#!/usr/bin/env bash
set -euo pipefail
if [[ "$1" == "pkey" ]]; then exit 0; fi
if [[ "$1" == "base64" ]]; then /usr/bin/base64 -w0; exit 0; fi
if [[ "$1" == "dgst" ]]; then printf 'signed'; exit 0; fi
exit 2
""",
    )
    _write_executable(
        bin_dir / "curl",
        f"""#!/usr/bin/env bash
set -euo pipefail
output=''
url=''
body=''
while (($#)); do
  case "$1" in
    --output) output="$2"; shift 2 ;;
    --url) url="$2"; shift 2 ;;
    --data) body="$2"; shift 2 ;;
    *) shift ;;
  esac
done
printf '%s\t%s\n' "$url" "$body" >> "$CURL_TEST_LOG"
if [[ "$url" == */installation ]]; then
  printf '{{"id":2468}}' > "$output"
elif [[ "$url" == */access_tokens ]]; then
  printf '%s' '{{"token":"{STATELESS_TOKEN}"}}' > "$output"
elif [[ "$url" == */repos/Boswell-Digital-Solutions/* ]]; then
  repository="${{url##*/}}"
  [[ "${{GITHUB_REPO_PROBE_FAIL:-}}" != "$repository" ]] || exit 22
  printf '{{"name":"%s","private":true}}' "$repository" > "$output"
else
  exit 2
fi
""",
    )
    _write_executable(
        bin_dir / "git",
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$GIT_TEST_LOG"
if [[ "${1:-}" == "credential" && "${2:-}" == "approve" ]]; then
  cat >> "$GIT_CREDENTIAL_LOG"
fi
""",
    )
    return bin_dir, git_log, curl_log, credential_log


def _base_env(
    bin_dir: Path,
    git_log: Path,
    curl_log: Path,
    credential_log: Path,
) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "GIT_TEST_LOG": str(git_log),
            "CURL_TEST_LOG": str(curl_log),
            "GIT_CREDENTIAL_LOG": str(credential_log),
            "GIT_CONFIG_GLOBAL": str(git_log.parent / "gitconfig"),
            "TMPDIR": str(git_log.parent),
            "RENDER": "true",
        }
    )
    for key in (
        "FORGE_PRIVATE_DEPS_APP_CLIENT_ID",
        "FORGE_PRIVATE_DEPS_APP_PRIVATE_KEY",
        "FORGE_TELEMETRY_TOKEN",
        "GITHUB_TOKEN",
    ):
        env.pop(key, None)
    return env


class RenderGitAuthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_mints_scoped_app_token_for_both_repositories(self) -> None:
        bin_dir, git_log, curl_log, credential_log = _fake_tools(self.tmp_path)
        env = _base_env(bin_dir, git_log, curl_log, credential_log)
        env.update(
            {
                "FORGE_PRIVATE_DEPS_APP_CLIENT_ID": " Iv23.client-id \n",
                "FORGE_PRIVATE_DEPS_APP_PRIVATE_KEY": "PRIVATE-PEM-CONTENT",
            }
        )

        result = subprocess.run(
            ["bash", str(SCRIPT)],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("short-lived BDS Fleet Operator auth configured", result.stdout)
        self.assertNotIn("PRIVATE-PEM-CONTENT", result.stdout + result.stderr)
        self.assertNotIn(STATELESS_TOKEN, result.stdout + result.stderr)

        curl_calls = curl_log.read_text(encoding="utf-8")
        self.assertIn(
            'access_tokens\t{"repositories":["forge-telemetry",'
            '"forge_contract_core"],"permissions":{"contents":"read"}}',
            curl_calls,
        )
        for repository in PRIVATE_REPOS:
            self.assertIn(
                f"/repos/Boswell-Digital-Solutions/{repository}\t", curl_calls
            )

        git_args = git_log.read_text(encoding="utf-8")
        self.assertNotIn(STATELESS_TOKEN, git_args)
        self.assertNotIn("url.https://x-access-token:", git_args)
        self.assertIn("credential.https://github.com.useHttpPath true", git_args)
        for repository in PRIVATE_REPOS:
            self.assertIn(
                "credential.https://github.com/Boswell-Digital-Solutions/"
                f"{repository}.git.helper",
                git_args,
            )

        credentials = credential_log.read_text(encoding="utf-8")
        self.assertEqual(credentials.count("username=x-access-token"), 2)
        for repository in PRIVATE_REPOS:
            self.assertIn(
                f"path=Boswell-Digital-Solutions/{repository}.git", credentials
            )

    def test_real_git_flow_removes_stale_root_rewrite_and_fills_both_paths(
        self,
    ) -> None:
        bin_dir, git_log, curl_log, credential_log = _fake_tools(self.tmp_path)
        (bin_dir / "git").unlink()
        env = _base_env(bin_dir, git_log, curl_log, credential_log)
        env.update(
            {
                "FORGE_PRIVATE_DEPS_APP_CLIENT_ID": "Iv23.client-id",
                "FORGE_PRIVATE_DEPS_APP_PRIVATE_KEY": "PRIVATE-PEM-CONTENT",
            }
        )
        stale_key = "url.https://x-access-token:stale@github.com/.insteadOf"
        subprocess.run(
            ["git", "config", "--global", stale_key, "https://github.com/"],
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        for repository in PRIVATE_REPOS:
            helper_key = (
                "credential.https://github.com/Boswell-Digital-Solutions/"
                f"{repository}.git.helper"
            )
            for stale_helper in (
                "cache --timeout=300",
                f"store --file={self.tmp_path}/stale-credentials",
            ):
                subprocess.run(
                    [
                        "git",
                        "config",
                        "--global",
                        "--add",
                        helper_key,
                        stale_helper,
                    ],
                    env=env,
                    check=True,
                    capture_output=True,
                    text=True,
                )

        result = subprocess.run(
            ["bash", str(SCRIPT)],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        stale_rewrites = subprocess.run(
            [
                "git",
                "config",
                "--global",
                "--get-regexp",
                r"^url\..*\.insteadof$",
            ],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(stale_rewrites.returncode, 1)

        for repository in PRIVATE_REPOS:
            helper_key = (
                "credential.https://github.com/Boswell-Digital-Solutions/"
                f"{repository}.git.helper"
            )
            helpers = subprocess.run(
                ["git", "config", "--global", "--get-all", helper_key],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(helpers.returncode, 0, helpers.stderr)
            self.assertEqual(len(helpers.stdout.splitlines()), 2)
            self.assertEqual(helpers.stdout.splitlines()[0], "")
            self.assertIn("store --file=", helpers.stdout.splitlines()[1])
            self.assertNotIn("stale-credentials", helpers.stdout)

            credential = subprocess.run(
                ["git", "credential", "fill"],
                input=(
                    "protocol=https\n"
                    "host=github.com\n"
                    f"path=Boswell-Digital-Solutions/{repository}.git\n\n"
                ),
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(credential.returncode, 0, credential.stderr)
            fields = dict(
                line.split("=", 1)
                for line in credential.stdout.splitlines()
                if "=" in line
            )
            self.assertEqual(fields.get("username"), "x-access-token")
            self.assertEqual(fields.get("password"), STATELESS_TOKEN)

    def test_fails_before_git_configuration_when_scoped_token_cannot_read_repo(
        self,
    ) -> None:
        bin_dir, git_log, curl_log, credential_log = _fake_tools(self.tmp_path)
        env = _base_env(bin_dir, git_log, curl_log, credential_log)
        env.update(
            {
                "FORGE_PRIVATE_DEPS_APP_CLIENT_ID": "Iv23.client-id",
                "FORGE_PRIVATE_DEPS_APP_PRIVATE_KEY": "PRIVATE-PEM-CONTENT",
                "GITHUB_REPO_PROBE_FAIL": "forge_contract_core",
            }
        )

        result = subprocess.run(
            ["bash", str(SCRIPT)],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("minted installation token cannot read", result.stderr)
        self.assertNotIn("PRIVATE-PEM-CONTENT", result.stdout + result.stderr)
        self.assertNotIn(STATELESS_TOKEN, result.stdout + result.stderr)
        self.assertFalse(git_log.exists())
        self.assertFalse(credential_log.exists())

    def test_incomplete_app_pair_fails_closed_before_legacy_fallback(self) -> None:
        bin_dir, git_log, curl_log, credential_log = _fake_tools(self.tmp_path)
        env = _base_env(bin_dir, git_log, curl_log, credential_log)
        env.update(
            {
                "FORGE_PRIVATE_DEPS_APP_CLIENT_ID": "Iv23.client-id",
                "FORGE_TELEMETRY_TOKEN": "legacy-token-must-not-be-used",
            }
        )

        result = subprocess.run(
            ["bash", str(SCRIPT)],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("must be configured as one complete pair", result.stderr)
        self.assertFalse(git_log.exists())

    def test_render_without_any_supported_credential_fails_closed(self) -> None:
        bin_dir, git_log, curl_log, credential_log = _fake_tools(self.tmp_path)
        env = _base_env(bin_dir, git_log, curl_log, credential_log)

        result = subprocess.run(
            ["bash", str(SCRIPT)],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("no private-dependency credential is configured", result.stderr)
        self.assertFalse(git_log.exists())


if __name__ == "__main__":
    unittest.main()
