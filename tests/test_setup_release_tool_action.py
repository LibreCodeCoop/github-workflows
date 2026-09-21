# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "actions" / "setup-release-tool" / "setup.sh"
ACTION = ROOT / "actions" / "setup-release-tool" / "action.yml"


class SetupReleaseToolActionTest(unittest.TestCase):
    def run_script(self, version: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            path_file = root / "path"
            env = os.environ | {
                "RELEASE_TOOL_VERSION": version,
                "RUNNER_TEMP": str(root),
                "GITHUB_OUTPUT": str(output),
                "GITHUB_PATH": str(path_file),
            }
            return subprocess.run(
                ["bash", str(SCRIPT)],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

    def test_action_exposes_only_exact_version_input(self) -> None:
        content = ACTION.read_text(encoding="utf-8")

        self.assertIn("version:", content)
        self.assertNotIn("latest", content.lower())
        self.assertIn("setup.sh", content)

    def test_rejects_latest_before_network_access(self) -> None:
        result = self.run_script("latest")

        self.assertEqual(2, result.returncode)
        self.assertIn("exact semantic version", result.stdout)

    def test_rejects_semver_range_before_network_access(self) -> None:
        result = self.run_script("^1.2.3")

        self.assertEqual(2, result.returncode)
        self.assertIn("exact semantic version", result.stdout)

    def test_script_downloads_phar_and_published_checksum_from_same_exact_tag(self) -> None:
        content = SCRIPT.read_text(encoding="utf-8")

        self.assertIn("releases/download/v${version}", content)
        self.assertIn("release-tool.phar.sha256", content)
        self.assertIn("sha256sum", content)
        self.assertIn("checksum mismatch", content)


if __name__ == "__main__":
    unittest.main()
