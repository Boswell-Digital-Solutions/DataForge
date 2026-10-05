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


TEL_TOKEN = "ghs_TELEMETRY_" + ("a" * 200)
CC_TOKEN = "ghs_CONTRACT_" + ("b" * 200)
LEGACY_CANARY = "legacy-canary-must-never-be-used"
TEL_KEY = "TELEMETRY-PEM-CONTENT"
CC_KEY = "CONTRACT-PEM-CONTENT"
SPLIT_VARS = (
    "FORGE_TELEMETRY_APP_CLIENT_ID",
    "FORGE_TELEMETRY_APP_PRIVATE_KEY",
    "FORGE_CONTRACT_CORE_APP_CLIENT_ID",
    "FORGE_CONTRACT_CORE_APP_PRIVATE_KEY",
)


def _split_tools(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    """Fake openssl, curl and git. Each repository's token reaches its own repository only."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    git_log = tmp_path / "git.log"
    curl_log = tmp_path / "curl.log"
    credential_log = tmp_path / "credential.log"

    _write_executable(
        bin_dir / "openssl",
        """#!/usr/bin/env bash
set -euo pipefail
if [[ "$1" == "pkey" ]]; then
  if grep -q INVALID "$3"; then exit 1; fi
  exit 0
fi
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
bearer=''
while (($#)); do
  case "$1" in
    --output) output="$2"; shift 2 ;;
    --url) url="$2"; shift 2 ;;
    --data) body="$2"; shift 2 ;;
    --header)
      case "$2" in "Authorization: Bearer "*) bearer="${{2#Authorization: Bearer }}" ;; esac
      shift 2 ;;
    *) shift ;;
  esac
done
printf '%s\t%s\n' "$url" "$body" >> "$CURL_TEST_LOG"
if [[ "$url" == */installation ]]; then
  iss="$(printf '%s' "$bearer" | cut -d. -f2 | tr '_-' '/+' | python3 -c "import sys,base64,json;d=sys.stdin.read().strip();d+='='*(-len(d)%4);print(json.loads(base64.b64decode(d))['iss'])")"
  [[ "$iss" != "${{APP_REJECT_CLIENT:-}}" ]] || exit 22
  printf '{{"id":2468}}' > "$output"
elif [[ "$url" == */access_tokens ]]; then
  if [[ "$body" == *'"repositories":["forge-telemetry"]'* ]]; then token='{TEL_TOKEN}'; repo=forge-telemetry
  elif [[ "$body" == *'"repositories":["forge_contract_core"]'* ]]; then token='{CC_TOKEN}'; repo=forge_contract_core
  else token='{STATELESS_TOKEN}'; repo=both; fi
  [[ "${{TOKEN_REFUSED_FOR:-}}" != "$repo" ]] || exit 22
  printf '{{"token":"%s"}}' "$token" > "$output"
elif [[ "$url" == */repos/Boswell-Digital-Solutions/* ]]; then
  repository="${{url##*/}}"
  [[ "${{GITHUB_REPO_PROBE_FAIL:-}}" != "$repository" ]] || exit 22
  if [[ "$bearer" == '{TEL_TOKEN}' && "$repository" != forge-telemetry && -z "${{LEAK_TEL:-}}" ]]; then exit 22; fi
  if [[ "$bearer" == '{CC_TOKEN}' && "$repository" != forge_contract_core && -z "${{LEAK_CC:-}}" ]]; then exit 22; fi
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


class RenderGitAuthSplitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)
        self.bin_dir, self.git_log, self.curl_log, self.credential_log = _split_tools(
            self.tmp_path
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _env(self, **extra: str) -> dict[str, str]:
        env = _base_env(self.bin_dir, self.git_log, self.curl_log, self.credential_log)
        for key in SPLIT_VARS:
            env.pop(key, None)
        env.update(
            {
                "FORGE_BUILD_AUTH_MODE": "split",
                "FORGE_TELEMETRY_APP_CLIENT_ID": " Iv23.tel-id \n",
                "FORGE_TELEMETRY_APP_PRIVATE_KEY": TEL_KEY,
                "FORGE_CONTRACT_CORE_APP_CLIENT_ID": "Iv23.cc-id",
                "FORGE_CONTRACT_CORE_APP_PRIVATE_KEY": CC_KEY,
                # Legacy credentials are present on purpose. Split mode must never use them.
                "FORGE_PRIVATE_DEPS_APP_CLIENT_ID": "Iv23.legacy-id",
                "FORGE_PRIVATE_DEPS_APP_PRIVATE_KEY": LEGACY_CANARY,
                "FORGE_TELEMETRY_TOKEN": LEGACY_CANARY,
                "GITHUB_TOKEN": LEGACY_CANARY,
            }
        )
        env.update(extra)
        return env

    def _run(self, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(SCRIPT)], env=env, text=True, capture_output=True, check=False
        )

    def _assert_no_secrets(self, result: subprocess.CompletedProcess[str]) -> None:
        output = result.stdout + result.stderr
        for secret in (TEL_KEY, CC_KEY, TEL_TOKEN, CC_TOKEN, STATELESS_TOKEN, LEGACY_CANARY):
            self.assertNotIn(secret, output)
        if self.git_log.exists():
            git_args = self.git_log.read_text(encoding="utf-8")
            for secret in (TEL_TOKEN, CC_TOKEN, LEGACY_CANARY):
                self.assertNotIn(secret, git_args)
            self.assertNotIn("url.https://x-access-token:", git_args)

    def _assert_nothing_configured(self) -> None:
        self.assertFalse(self.git_log.exists())
        self.assertFalse(self.credential_log.exists())

    def test_split_mode_mints_one_token_per_repository(self) -> None:
        result = self._run(self._env())

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("split-mode auth configured", result.stdout)
        self._assert_no_secrets(result)

        curl_calls = self.curl_log.read_text(encoding="utf-8")
        self.assertIn('access_tokens\t{"repositories":["forge-telemetry"],"permissions":{"contents":"read"}}', curl_calls)
        self.assertIn('access_tokens\t{"repositories":["forge_contract_core"],"permissions":{"contents":"read"}}', curl_calls)
        # No request names both repositories.
        self.assertNotIn('"forge-telemetry","forge_contract_core"', curl_calls)

        credentials = self.credential_log.read_text(encoding="utf-8")
        entries = [e for e in credentials.split("\n\n") if e.strip()]
        self.assertEqual(len(entries), 2)
        by_path = {}
        for entry in entries:
            fields = dict(line.split("=", 1) for line in entry.splitlines() if "=" in line)
            by_path[fields["path"]] = fields["password"]
        self.assertEqual(by_path["Boswell-Digital-Solutions/forge-telemetry.git"], TEL_TOKEN)
        self.assertEqual(by_path["Boswell-Digital-Solutions/forge_contract_core.git"], CC_TOKEN)
        # The legacy canary never reached a request or a stored credential.
        self.assertNotIn(LEGACY_CANARY, curl_calls + credentials)

    def test_split_mode_real_git_gives_each_path_its_own_token(self) -> None:
        (self.bin_dir / "git").unlink()
        env = self._env()
        result = self._run(env)
        self.assertEqual(result.returncode, 0, result.stderr)
        for repository, expected in (
            ("forge-telemetry", TEL_TOKEN),
            ("forge_contract_core", CC_TOKEN),
        ):
            credential = subprocess.run(
                ["git", "credential", "fill"],
                input=(
                    "protocol=https\nhost=github.com\n"
                    f"path=Boswell-Digital-Solutions/{repository}.git\n\n"
                ),
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(credential.returncode, 0, credential.stderr)
            fields = dict(
                line.split("=", 1) for line in credential.stdout.splitlines() if "=" in line
            )
            self.assertEqual(fields.get("password"), expected)

    def test_split_mode_fails_closed_when_any_value_is_missing(self) -> None:
        for missing in SPLIT_VARS:
            with self.subTest(missing=missing):
                for path in (self.git_log, self.curl_log, self.credential_log):
                    path.unlink(missing_ok=True)
                env = self._env()
                env.pop(missing)
                result = self._run(env)
                self.assertEqual(result.returncode, 1)
                self.assertIn("No fallback credential is used", result.stderr)
                self._assert_nothing_configured()
                self.assertFalse(self.curl_log.exists())
                self._assert_no_secrets(result)

    def test_split_mode_fails_closed_on_an_invalid_key(self) -> None:
        result = self._run(self._env(FORGE_CONTRACT_CORE_APP_PRIVATE_KEY="INVALID-KEY"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("FORGE_CONTRACT_CORE_APP_PRIVATE_KEY is not a valid PEM", result.stderr)
        self._assert_nothing_configured()
        self._assert_no_secrets(result)

    def test_split_mode_fails_closed_when_github_rejects_an_app(self) -> None:
        result = self._run(self._env(APP_REJECT_CLIENT="Iv23.cc-id"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("contract-core build App credentials were rejected", result.stderr)
        self._assert_nothing_configured()
        self._assert_no_secrets(result)

    def test_split_mode_fails_closed_when_a_token_is_refused(self) -> None:
        result = self._run(self._env(TOKEN_REFUSED_FOR="forge_contract_core"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("refused a read-only installation token for the contract-core build App", result.stderr)
        # The telemetry token was minted, but nothing is configured and no legacy path runs.
        self._assert_nothing_configured()
        self.assertNotIn(LEGACY_CANARY, self.curl_log.read_text(encoding="utf-8"))
        self._assert_no_secrets(result)

    def test_split_mode_fails_when_a_token_cannot_read_its_own_repository(self) -> None:
        result = self._run(self._env(GITHUB_REPO_PROBE_FAIL="forge-telemetry"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot read Boswell-Digital-Solutions/forge-telemetry", result.stderr)
        self._assert_nothing_configured()
        self._assert_no_secrets(result)

    def test_split_mode_fails_when_a_token_reaches_the_other_repository(self) -> None:
        for leak, label in (("LEAK_TEL", "telemetry"), ("LEAK_CC", "contract-core")):
            with self.subTest(leak=leak):
                for path in (self.git_log, self.curl_log, self.credential_log):
                    path.unlink(missing_ok=True)
                result = self._run(self._env(**{leak: "1"}))
                self.assertEqual(result.returncode, 1)
                self.assertIn(f"the {label} build App token can read", result.stderr)
                self.assertIn("outside its scope", result.stderr)
                self._assert_nothing_configured()
                self._assert_no_secrets(result)

    def test_unknown_mode_is_refused(self) -> None:
        result = self._run(self._env(FORGE_BUILD_AUTH_MODE="Split"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("must be 'legacy' or 'split'", result.stderr)
        self._assert_nothing_configured()

    def test_default_mode_stays_legacy_and_ignores_split_variables(self) -> None:
        env = self._env()
        env.pop("FORGE_BUILD_AUTH_MODE")
        env["FORGE_PRIVATE_DEPS_APP_PRIVATE_KEY"] = "PRIVATE-PEM-CONTENT"
        result = self._run(env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("short-lived BDS Fleet Operator auth configured", result.stdout)
        curl_calls = self.curl_log.read_text(encoding="utf-8")
        self.assertIn('"repositories":["forge-telemetry","forge_contract_core"]', curl_calls)

    def test_default_mode_without_legacy_credentials_does_not_use_split_variables(self) -> None:
        env = self._env()
        env.pop("FORGE_BUILD_AUTH_MODE")
        for key in ("FORGE_PRIVATE_DEPS_APP_CLIENT_ID", "FORGE_PRIVATE_DEPS_APP_PRIVATE_KEY", "FORGE_TELEMETRY_TOKEN", "GITHUB_TOKEN"):
            env.pop(key)
        result = self._run(env)
        self.assertEqual(result.returncode, 1)
        self.assertIn("no private-dependency credential is configured", result.stderr)
        self._assert_nothing_configured()


if __name__ == "__main__":
    unittest.main()
