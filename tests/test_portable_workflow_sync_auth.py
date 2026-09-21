# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "workflow-templates" / "sync-workflow-templates.yml"


class PortableWorkflowSyncAuthTest(unittest.TestCase):
    def test_template_supports_explicit_authentication_modes(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")

        self.assertIn("WORKFLOW_SYNC_AUTH_MODE", content)
        self.assertIn("librecode-app", content)
        self.assertIn("github-app", content)
        self.assertIn("token", content)
        self.assertIn("github-token", content)
        self.assertIn("WORKFLOW_SYNC_APP_ID", content)
        self.assertIn("WORKFLOW_SYNC_APP_PRIVATE_KEY", content)
        self.assertIn("WORKFLOW_SYNC_TOKEN", content)

    def test_external_modes_do_not_require_librecode_credentials(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")

        self.assertIn("Create consumer GitHub App token", content)
        self.assertIn("vars.WORKFLOW_SYNC_AUTH_MODE == 'github-app'", content)
        self.assertIn('github-app) token="${CONSUMER_APP_TOKEN}"', content)
        self.assertIn('token) token="${CONSUMER_TOKEN}"', content)

    def test_generated_pull_request_uses_selected_token(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")

        self.assertIn("id: auth-token", content)
        self.assertIn("token: ${{ steps.auth-token.outputs.token }}", content)

    def test_github_token_limitation_is_visible_in_template(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("GITHUB_TOKEN limitations", content)
        self.assertIn("docs/cross-repository-automation.md", content)

    def test_sync_action_is_pinned_with_release_and_catalog_provenance(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")

        self.assertIn(
            "actions/sync-workflows@002f17274ba1eade3351ba81890bf53674b37c43 # v0.4.0",
            content,
        )
        self.assertIn("platform-version: v0.4.0", content)
        self.assertIn(
            "source-commit: 002f17274ba1eade3351ba81890bf53674b37c43",
            content,
        )
        self.assertIn("id: catalog-revision", content)
        self.assertIn(
            "catalog-commit: ${{ steps.catalog-revision.outputs.sha }}",
            content,
        )


if __name__ == "__main__":
    unittest.main()
