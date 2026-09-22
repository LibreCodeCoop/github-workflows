# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / "actions" / "release-publication" / "action.yml"


class ReleasePublicationActionTest(unittest.TestCase):
    def test_restores_state_from_post_merge_run(self) -> None:
        content = ACTION.read_text(encoding="utf-8")
        self.assertIn("release-state-${{ inputs.github-release-id }}", content)
        self.assertIn("post-merge-event:", content)
        self.assertIn("default: pull_request", content)
        self.assertIn("expected-event: ${{ inputs.post-merge-event }}", content)
        self.assertIn("expected-workflow-path:", content)

    def test_retry_loop_reuses_publication_verify_contract(self) -> None:
        content = ACTION.read_text(encoding="utf-8")
        self.assertIn("publication:verify", content)
        self.assertIn("--draft", content)
        self.assertIn("--prepared", content)
        self.assertIn("RELEASE_ATTEMPTS", content)
        self.assertIn("RELEASE_DELAY_SECONDS", content)
        self.assertNotIn("apps.nextcloud.com", content)
        self.assertNotIn("actions/workflows", content)

    def test_persists_publication_verification_artifact(self) -> None:
        content = ACTION.read_text(encoding="utf-8")
        self.assertIn('artifact_name="publication-verification-${RELEASE_ID}"', content)
        self.assertIn("actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02", content)


if __name__ == "__main__":
    unittest.main()
