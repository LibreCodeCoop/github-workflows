# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "actions" / "setup-release-tool" / "setup.sh"
ACTION = ROOT / "actions" / "setup-release-tool" / "action.yml"
VERSION = ROOT / "actions" / "setup-release-tool" / "release-tool-version"


class SetupReleaseToolActionTest(unittest.TestCase):
    def run_script(
        self,
        version: str | None,
        *,
        fake_download: bool = False,
        checksum_mismatch: bool = False,
        missing_artifact: bool = False,
    ) -> tuple[subprocess.CompletedProcess[str], str, str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            path_file = root / "path"
            env = os.environ | {
                "GITHUB_ACTION_PATH": str(SCRIPT.parent),
                "RUNNER_TEMP": str(root),
                "GITHUB_OUTPUT": str(output),
                "GITHUB_PATH": str(path_file),
            }

            if version is not None:
                env["RELEASE_TOOL_VERSION"] = version

            if fake_download:
                fake_bin = root / "bin"
                fake_bin.mkdir()
                curl = fake_bin / "curl"
                curl.write_text(
                    "#!/usr/bin/env bash\n"
                    "set -euo pipefail\n"
                    "output=''\n"
                    "url=''\n"
                    "while (($#)); do\n"
                    "  case \"$1\" in\n"
                    "    --output) output=\"$2\"; shift 2 ;;\n"
                    "    http*) url=\"$1\"; shift ;;\n"
                    "    *) shift ;;\n"
                    "  esac\n"
                    "done\n"
                    "if [[ \"${FAKE_MISSING_ARTIFACT:-0}\" == 1 && \"$url\" == *.phar ]]; then\n"
                    "  exit 22\n"
                    "fi\n"
                    "if [[ \"$url\" == *.sha256 ]]; then\n"
                    "  if [[ \"${FAKE_CHECKSUM_MISMATCH:-0}\" == 1 ]]; then\n"
                    "    printf '%064d  release-tool.phar\\n' 0 > \"$output\"\n"
                    "  else\n"
                    "    printf fake-phar | sha256sum | awk '{print $1 \"  release-tool.phar\"}' > \"$output\"\n"
                    "  fi\n"
                    "else\n"
                    "  printf fake-phar > \"$output\"\n"
                    "fi\n",
                    encoding="utf-8",
                )
                curl.chmod(0o755)

                php = fake_bin / "php"
                php.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
                php.chmod(0o755)

                env["PATH"] = str(fake_bin) + os.pathsep + env["PATH"]
                if checksum_mismatch:
                    env["FAKE_CHECKSUM_MISMATCH"] = "1"
                if missing_artifact:
                    env["FAKE_MISSING_ARTIFACT"] = "1"

            result = subprocess.run(
                ["bash", str(SCRIPT)],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            return (
                result,
                output.read_text(encoding="utf-8") if output.exists() else "",
                path_file.read_text(encoding="utf-8") if path_file.exists() else "",
            )

    def test_action_exposes_optional_exact_version_override(self) -> None:
        content = ACTION.read_text(encoding="utf-8")

        self.assertIn("version:", content)
        self.assertIn("required: false", content)
        self.assertIn("default: ''", content)
        self.assertIn("setup.sh", content)

    def test_default_version_is_centralized_in_action_directory(self) -> None:
        result, output, path_file = self.run_script(None, fake_download=True)

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("version=0.5.0", output)
        self.assertIn("librecode-release-tool/0.5.0", path_file)

    def test_rejects_latest_before_network_access(self) -> None:
        result, _, _ = self.run_script("latest")

        self.assertEqual(2, result.returncode)
        self.assertIn("exact semantic version", result.stdout)

    def test_rejects_semver_range_before_network_access(self) -> None:
        result, _, _ = self.run_script("^1.2.3")

        self.assertEqual(2, result.returncode)
        self.assertIn("exact semantic version", result.stdout)

    def test_valid_exact_release_is_verified_and_exposed(self) -> None:
        result, output, path_file = self.run_script("1.2.3", fake_download=True)

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("version=1.2.3", output)
        self.assertIn("path=", output)
        self.assertIn("librecode-release-tool/1.2.3", path_file)

    def test_checksum_mismatch_fails_closed(self) -> None:
        result, output, _ = self.run_script(
            "1.2.3",
            fake_download=True,
            checksum_mismatch=True,
        )

        self.assertEqual(3, result.returncode)
        self.assertIn("checksum mismatch", result.stdout)
        self.assertEqual("", output)

    def test_missing_artifact_fails_closed(self) -> None:
        result, output, _ = self.run_script(
            "1.2.3",
            fake_download=True,
            missing_artifact=True,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertEqual("", output)

    def test_script_downloads_phar_and_published_checksum_from_same_exact_tag(self) -> None:
        content = SCRIPT.read_text(encoding="utf-8")

        self.assertIn("releases/download/v${version}", content)
        self.assertIn("release-tool.phar.sha256", content)
        self.assertIn("sha256sum", content)
        self.assertEqual("0.5.0", VERSION.read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    unittest.main()
