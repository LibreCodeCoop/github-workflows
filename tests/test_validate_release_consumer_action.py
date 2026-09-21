# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / "actions" / "validate-release-consumer" / "action.yml"
SCRIPT = ROOT / "actions" / "validate-release-consumer" / "validate.sh"


class ValidateReleaseConsumerActionTest(unittest.TestCase):
    def test_action_wraps_setup_and_exposes_normalized_outputs(self) -> None:
        content = ACTION.read_text(encoding="utf-8")

        self.assertIn("uses: $/actions/setup-release-tool", content)
        for output in (
            "version:",
            "major:",
            "development:",
            "changelog-path:",
            "tool-version:",
        ):
            self.assertIn(output, content)

    def test_script_validates_config_and_metadata_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            output = root / "output"
            calls = root / "calls"

            php = fake_bin / "php"
            php.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "printf '%s\\n' \"$*\" >> \"${CALLS_FILE}\"\n"
                "if [[ \"$*\" == *'config:validate'* ]]; then exit 0; fi\n"
                "if [[ \"$*\" == *'metadata:inspect'* ]]; then\n"
                "  cat <<'JSON'\n"
                "{\"schema\":1,\"valid\":true,\"version\":\"16.0.0-dev.2\",\"major\":16,\"development\":true,\"changelog_path\":\"docs/changelogs/changelog-16.md\"}\n"
                "JSON\n"
                "  exit 0\n"
                "fi\n"
                "exec /usr/bin/php \"$@\"\n",
                encoding="utf-8",
            )
            php.chmod(0o755)

            env = os.environ | {
                "PATH": str(fake_bin) + os.pathsep + os.environ["PATH"],
                "CALLS_FILE": str(calls),
                "RELEASE_TOOL_PATH": "/tmp/release-tool.phar",
                "RELEASE_CONFIG_PATH": ".nextcloud-release.yml",
                "RELEASE_ROOT": ".",
                "RELEASE_REF": "HEAD",
                "RUNNER_TEMP": str(root),
                "GITHUB_OUTPUT": str(output),
            }

            result = subprocess.run(
                ["bash", str(SCRIPT)],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            called = calls.read_text(encoding="utf-8")
            self.assertIn("config:validate", called)
            self.assertIn("metadata:inspect", called)

            outputs = output.read_text(encoding="utf-8")
            self.assertIn("version=16.0.0-dev.2", outputs)
            self.assertIn("major=16", outputs)
            self.assertIn("development=true", outputs)
            self.assertIn(
                "changelog-path=docs/changelogs/changelog-16.md",
                outputs,
            )


if __name__ == "__main__":
    unittest.main()
