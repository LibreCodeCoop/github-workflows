# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / "actions" / "release-post-merge" / "action.yml"
RESTORE = ROOT / "actions" / "release-artifact-restore" / "action.yml"


class ReleasePostMergeActionTest(unittest.TestCase):
    def test_credentials_are_validated_before_artifact_restore(self) -> None:
        content = ACTION.read_text(encoding="utf-8")
        validate = content.index("Validate GitHub App credentials")
        restore = content.index("Restore preparation contracts")
        self.assertLess(validate, restore)
        self.assertIn("LIBRECODE_WORKFLOW_APP_PRIVATE_KEY", content)
        self.assertIn("librecode-workflow-automation", content)
        self.assertIn("/apps/${RELEASE_APP_SLUG}", content)
        self.assertNotIn("\n  app-id:", content)
        self.assertNotIn("inputs.app-id", content)

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

    def test_mutating_stages_use_scoped_tokens(self) -> None:
        content = ACTION.read_text(encoding="utf-8")
        self.assertEqual(2, content.count("actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1"))
        self.assertEqual(2, content.count("client-id: ${{ steps.app-identity.outputs.client-id }}"))
        self.assertIn("permission-contents: write", content)
        self.assertIn("permission-pull-requests: write", content)
        self.assertNotIn("permission-issues: write", content)
        self.assertIn("permission-pull-requests: read", content)
        self.assertIn("GITHUB_TOKEN: ${{ inputs.github-token }}", content)

    def test_release_draft_errors_are_exposed(self) -> None:
        content = ACTION.read_text(encoding="utf-8")
        draft = content.index("Create or update GitHub Release draft")
        tail = content[draft:]
        self.assertIn('status=$?', tail)
        self.assertIn('cat "${RELEASE_STATE_DIR}/release-draft.json" || true', tail)

    def test_contract_chain_is_persisted_for_publication(self) -> None:
        content = ACTION.read_text(encoding="utf-8")
        self.assertIn("release:finalize", content)
        self.assertIn("milestone:transition", content)
        self.assertIn("release:draft", content)
        self.assertIn('artifact_name="release-state-${release_id}"', content)
        self.assertIn("actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a", content)

    def test_restore_action_can_bind_artifact_to_origin_workflow(self) -> None:
        content = RESTORE.read_text(encoding="utf-8")
        self.assertIn("expected-event:", content)
        self.assertIn("expected-workflow-path:", content)


if __name__ == "__main__":
    unittest.main()
