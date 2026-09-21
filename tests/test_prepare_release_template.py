# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "workflow-templates" / "prepare-release.yml"
CATALOG = ROOT / "workflow-catalog.json"


class PrepareReleaseTemplateTest(unittest.TestCase):
    def test_template_is_published_and_legacy_release_template_is_not(self) -> None:
        import json

        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        self.assertIn("prepare-release", catalog["templates"])
        self.assertNotIn("release-nextcloud-app", catalog["templates"])

    def test_template_exposes_required_release_entry_points(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch:", content)
        self.assertIn("pull_request:", content)
        self.assertIn("release:", content)
        self.assertIn("branch:", content)
        self.assertIn("channel:", content)
        self.assertIn("ignore_open_backport:", content)
        self.assertIn("create_follow_up_milestone:", content)
        self.assertIn("mode:", content)

    def test_template_delegates_all_release_stages_to_versioned_actions(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")
        sha = "002f17274ba1eade3351ba81890bf53674b37c43"

        self.assertIn(
            f"actions/release-prepare@{sha} # v0.4.0",
            content,
        )
        self.assertIn(
            f"actions/release-post-merge@{sha} # v0.4.0",
            content,
        )
        self.assertIn(
            f"actions/release-publication@{sha} # v0.4.0",
            content,
        )

    def test_template_keeps_permissions_stage_scoped(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")

        self.assertIn("permissions: {}", content)
        self.assertIn("actions: read", content)
        self.assertIn("contents: read", content)
        self.assertIn("pull-requests: read", content)
        self.assertNotIn("permissions: write-all", content)
        self.assertNotIn("contents: write", content)

    def test_post_merge_only_accepts_generated_merged_release_prs(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")

        self.assertIn("github.event.pull_request.merged == true", content)
        self.assertIn("startsWith(github.event.pull_request.head.ref, 'release-tool/')", content)
        self.assertIn("<!-- release-tool:preparation ", content)
        self.assertIn("github.event.pull_request.merged_by.login", content)


if __name__ == "__main__":
    unittest.main()
