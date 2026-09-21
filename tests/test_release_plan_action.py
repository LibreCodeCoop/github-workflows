# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / "actions" / "release-plan" / "action.yml"
WORKFLOW = ROOT / ".github" / "workflows" / "release-plan.yml"


class ReleasePlanActionTest(unittest.TestCase):
    def test_action_uses_exact_verified_release_tool(self) -> None:
        content = ACTION.read_text(encoding="utf-8")

        self.assertIn("uses: $/actions/setup-release-tool", content)
        self.assertNotIn("with:\n        version:", content)
        self.assertIn("release:plan", content)
        self.assertIn("--release-version", content)
        self.assertNotIn("python3", content)
        self.assertNotIn("release_plan.py", content)

    def test_action_exposes_release_plan_v1_inputs_and_outputs(self) -> None:
        content = ACTION.read_text(encoding="utf-8")

        for expected in (
            "branch:",
            "ref:",
            "version:",
            "channel:",
            "mode:",
            "safe-public-text:",
            "ignore-open-backport:",
            "create-follow-up-milestone:",
            "config-path:",
            "plan:",
            "ready:",
            "tool-version:",
        ):
            self.assertIn(expected, content)

        for transitional in (
            "blocker-queries:",
            "appinfo-path:",
            "changelog-path:",
        ):
            self.assertNotIn(transitional, content)

    def test_reusable_workflow_checks_out_full_release_history(self) -> None:
        content = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("fetch-depth: 0", content)
        self.assertIn("uses: $/actions/release-plan", content)
        self.assertIn("plan:", content)
        self.assertIn("ready:", content)
        self.assertIn("tool_version:", content)

    def test_step_summary_does_not_print_public_release_text(self) -> None:
        content = ACTION.read_text(encoding="utf-8")

        summary = content.split('echo "## Release plan"', 1)[1]
        self.assertNotIn('public_release_text', summary)


if __name__ == "__main__":
    unittest.main()
