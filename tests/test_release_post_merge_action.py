# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / "actions" / "release-post-merge" / "action.yml"
RESTORE = ROOT / "actions" / "release-artifact-restore" / "action.yml"


class ReleasePostMergeActionTest(unittest.TestCase):
    def test_authorization_happens_before_mutation(self) -> None:
        content = ACTION.read_text(encoding="utf-8")
        authorize = content.index("Authorize release PR merger")
        finalize = content.index("Revalidate merged release")
        milestone = content.index("Apply milestone transition")
        draft = content.index("Create or update GitHub Release draft")
        self.assertLess(authorize, finalize)
        self.assertLess(finalize, milestone)
        self.assertLess(milestone, draft)
        self.assertIn("merge_min_permission", content)

    def test_each_mutating_stage_uses_scoped_app_token(self) -> None:
        content = ACTION.read_text(encoding="utf-8")
        self.assertEqual(3, content.count("actions/create-github-app-token@67018539274d69449ef7c02e8e71183d1719ab42"))
        self.assertIn("permission-contents: write", content)
        self.assertIn("permission-pull-requests: write", content)
        self.assertIn("permission-issues: write", content)
        self.assertIn("permission-pull-requests: read", content)

    def test_contract_chain_is_persisted_for_publication(self) -> None:
        content = ACTION.read_text(encoding="utf-8")
        self.assertIn("release:finalize", content)
        self.assertIn("milestone:transition", content)
        self.assertIn("release:draft", content)
        self.assertIn('artifact_name="release-state-${release_id}"', content)
        self.assertIn("actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02", content)

    def test_restore_action_can_bind_artifact_to_origin_workflow(self) -> None:
        content = RESTORE.read_text(encoding="utf-8")
        self.assertIn("expected-event:", content)
        self.assertIn("expected-workflow-path:", content)


if __name__ == "__main__":
    unittest.main()
