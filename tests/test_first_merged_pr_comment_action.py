# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "actions" / "first-merged-pr-comment" / "first_merged_pr_comment.py"

spec = importlib.util.spec_from_file_location("first_merged_pr_comment", SCRIPT)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FirstMergedPrCommentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.pr = {
            "number": 42,
            "html_url": "https://git.example/acme/project/pull/42",
            "merged": True,
            "closed_at": "2026-09-23T12:00:00Z",
            "merge_commit_sha": "abc123",
            "user": {"login": "alice", "type": "User"},
        }

    def test_build_context_is_generic(self) -> None:
        context = module.build_context(
            pr=self.pr,
            repository="acme/project",
            server_url="https://git.example",
            api_url="https://git.example/api/v3",
        )
        self.assertEqual(context["server_url"], "https://git.example")
        self.assertEqual(context["repository"], "acme/project")
        self.assertEqual(context["repository_owner"], "acme")
        self.assertEqual(context["repository_name"], "project")
        self.assertEqual(context["repository_url"], "https://git.example/acme/project")
        self.assertEqual(context["pull_request_number"], "42")
        self.assertEqual(context["pull_request_url"], "https://git.example/acme/project/pull/42")
        self.assertEqual(context["contributor_login"], "alice")
        self.assertEqual(context["contributor_mention"], "@alice")
        self.assertEqual(context["contributor_url"], "https://git.example/alice")
        self.assertEqual(context["merge_commit_sha"], "abc123")

    def test_render_template_composes_arbitrary_urls(self) -> None:
        context = module.build_context(
            pr=self.pr,
            repository="acme/project",
            server_url="https://git.example",
            api_url="https://git.example/api/v3",
        )
        template = (
            "Hello {contributor_mention}. "
            "Docs: {repository_url}/docs. "
            "Survey: https://survey.example/form?repo={repository|urlencode}"
            "&user={contributor_login|urlencode}&pr={pull_request_number}."
        )
        rendered = module.render_template(template, context)
        self.assertEqual(
            rendered,
            "Hello @alice. Docs: https://git.example/acme/project/docs. "
            "Survey: https://survey.example/form?repo=acme%2Fproject"
            "&user=alice&pr=42.",
        )

    def test_render_template_rejects_unknown_placeholder(self) -> None:
        with self.assertRaisesRegex(module.ActionError, "unknown placeholder: survey_url"):
            module.render_template("{survey_url}", {"repository": "acme/project"})

    def test_render_template_rejects_unknown_filter(self) -> None:
        with self.assertRaisesRegex(module.ActionError, "unknown placeholder filter: shell"):
            module.render_template("{repository|shell}", {"repository": "acme/project"})

    def test_render_template_rejects_empty_message(self) -> None:
        with self.assertRaisesRegex(module.ActionError, "message template is empty"):
            module.render_template("   ", {})

    def test_first_merged_query_is_historical_for_safe_retries(self) -> None:
        query = module.first_merged_query(
            "acme/project",
            "alice",
            "2026-09-23T12:00:00Z",
        )
        self.assertEqual(
            query,
            "repo:acme/project is:pr is:merged author:alice "
            "closed:<=2026-09-23T12:00:00Z",
        )

    def test_marker_is_stable_for_idempotency(self) -> None:
        self.assertEqual(
            module.MARKER,
            "<!-- librecode:first-merged-pr-comment -->",
        )

    def test_action_contract_has_no_product_specific_inputs(self) -> None:
        action = (
            ROOT / "actions" / "first-merged-pr-comment" / "action.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("message-template:", action)
        self.assertIn("pull-request-number:", action)
        self.assertNotIn("survey", action.lower())
        self.assertNotIn("community", action.lower())
        self.assertNotIn("good first issue", action.lower())


if __name__ == "__main__":
    unittest.main()
