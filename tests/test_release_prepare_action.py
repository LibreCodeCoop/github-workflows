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
        self.assertIn("actions/create-github-app-token@67018539274d69449ef7c02e8e71183d1719ab42", content)
        self.assertIn("permission-contents: write", content)
        self.assertIn("permission-pull-requests: write", content)
        self.assertNotIn("permission-workflows: write", content)
        self.assertIn("release:prepare", content)

    def test_prepare_persists_plan_and_preparation_by_pr_number(self) -> None:
        content = ACTION.read_text(encoding="utf-8")
        self.assertIn("release-plan.json", content)
        self.assertIn("release-preparation.json", content)
        self.assertIn('artifact_name="release-preparation-pr-${pr_number}"', content)
        self.assertIn("actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02", content)


if __name__ == "__main__":
    unittest.main()
