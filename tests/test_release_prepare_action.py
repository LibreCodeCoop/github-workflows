# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / "actions" / "release-prepare" / "action.yml"
PLAN = ROOT / "actions" / "release-plan" / "action.yml"


class ReleasePrepareActionTest(unittest.TestCase):
    def test_plan_exposes_same_job_contract_paths(self) -> None:
        content = PLAN.read_text(encoding="utf-8")
        self.assertIn("tool-path:", content)
        self.assertIn("plan-path:", content)
        self.assertIn('echo "plan-path=${plan_file}"', content)

    def test_prepare_composes_policy_contracts_and_scoped_mutation(self) -> None:
        content = ACTION.read_text(encoding="utf-8")
        self.assertIn("$/actions/release-plan", content)
        self.assertIn("config:validate", content)
        self.assertIn("prepare_min_permission", content)
        self.assertIn("$/actions/release-authorization", content)
        self.assertIn("actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1", content)
        self.assertIn("permission-contents: write", content)
        self.assertIn("permission-pull-requests: write", content)
        self.assertNotIn("permission-workflows: write", content)
        self.assertIn("client-id: ${{ steps.app-identity.outputs.client-id }}", content)
        self.assertNotIn("app-id: ${{ inputs.app-id }}", content)
        self.assertIn("release:prepare", content)
        self.assertIn("Apply release pull request metadata", content)
        self.assertIn('"assignees"=>[$argv[1]]', content)
        self.assertIn('"milestone"=>(int)$argv[2]', content)

    def test_prepare_validates_mutation_credentials_before_planning(self) -> None:
        content = ACTION.read_text(encoding="utf-8")
        validate = content.index("Validate GitHub App credentials")
        plan = content.index("Build release plan")
        self.assertLess(validate, plan)
        self.assertIn("LIBRECODE_WORKFLOW_APP_PRIVATE_KEY", content)
        self.assertIn("librecode-workflow-automation", content)
        self.assertIn("/apps/${RELEASE_APP_SLUG}", content)
        self.assertIn('"client_id"', content)

    def test_prepare_persists_plan_and_preparation_by_pr_number(self) -> None:
        content = ACTION.read_text(encoding="utf-8")
        self.assertIn("release-plan.json", content)
        self.assertIn("release-preparation.json", content)
        self.assertIn('artifact_name="release-preparation-pr-${pr_number}"', content)
        self.assertIn("actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a", content)


if __name__ == "__main__":
    unittest.main()
