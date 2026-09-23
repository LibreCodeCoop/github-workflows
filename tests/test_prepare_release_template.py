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
        self.assertIn("pull_request_target:", content)
        self.assertIn("release:", content)
        self.assertIn("branch:", content)
        self.assertIn("channel:", content)
        self.assertIn("ignore_open_backport:", content)
        self.assertIn("create_follow_up_milestone:", content)
        self.assertNotIn("mode:", content)
        self.assertNotIn("safe_public_text:", content)

    def test_dispatch_help_is_concise_and_explains_risky_inputs(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")

        self.assertNotIn("description: Optional", content)
        self.assertIn("github.com/LibreSign/documentation/blob/main/developer_manual/release-process/preparing.rst", content)
        self.assertIn("Leave blank to use the latest branch state", content)
        self.assertIn("Branch and version rules are still validated", content)
        self.assertIn("matching backport PR still open", content)
        self.assertIn("move remaining open items", content)
        self.assertNotIn("advisory-private", content)
        self.assertNotIn("private advisory details", content)

    def test_template_uses_explicit_release_run_names(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")

        self.assertIn("run-name:", content)
        self.assertIn("Prepare release · {0}", content)
        self.assertIn("Finalize release · PR #{0}", content)
        self.assertIn("Verify release · {0}", content)

    def test_template_delegates_all_release_stages_to_versioned_actions(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")
        sha = "f732578ab87c7bd7d85b60ac1612277149f1153e"

        self.assertIn(
            f"actions/release-prepare@{sha} # v0.6.29",
            content,
        )
        self.assertIn(
            f"actions/release-post-merge@{sha} # v0.6.29",
            content,
        )
        self.assertIn(
            f"actions/release-publication@{sha} # v0.6.29",
            content,
        )

    def test_release_mutation_credentials_use_org_secret(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")

        self.assertNotIn("vars.LIBRECODE_WORKFLOW_APP_ID", content)
        self.assertEqual(2, content.count("secrets.LIBRECODE_WORKFLOW_APP_PRIVATE_KEY"))
        self.assertNotIn("secrets.LIBRECODE_WORKFLOW_APP_ID", content)

    def test_release_checkout_fetches_only_selected_branch_history_and_tags(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")

        self.assertIn("fetch-depth: 1", content)
        self.assertIn('refs/heads/${RELEASE_BRANCH}:refs/remotes/origin/${RELEASE_BRANCH}', content)
        self.assertIn('refs/tags/*:refs/tags/*', content)
        self.assertNotIn("fetch-depth: 0", content)

    def test_template_keeps_permissions_stage_scoped(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")

        self.assertIn("permissions: {}", content)
        self.assertIn("actions: read", content)
        self.assertIn("contents: read", content)
        self.assertIn("issues: write", content)
        self.assertIn("pull-requests: read", content)
        self.assertNotIn("permissions: write-all", content)
        self.assertNotIn("contents: write", content)

    def test_post_merge_only_accepts_generated_merged_release_prs(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")

        self.assertIn("github.event_name == 'pull_request_target'", content)
        self.assertIn("github.event.pull_request.merged == true", content)
        self.assertIn("startsWith(github.event.pull_request.head.ref, 'release-tool/')", content)
        self.assertIn("<!-- release-tool:preparation ", content)
        self.assertIn("github.event.pull_request.merged_by.login", content)


if __name__ == "__main__":
    unittest.main()
