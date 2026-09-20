# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from scripts.release_plan import PlanInput, build_plan, parse_blocker_queries


class ReleasePlanTest(unittest.TestCase):
    def fixture(self, directory: str, version: str = "16.0.0") -> PlanInput:
        root = Path(directory)
        appinfo = root / "appinfo/info.xml"
        appinfo.parent.mkdir(parents=True)
        appinfo.write_text(
            f"<info><version>{version}</version></info>",
            encoding="utf-8",
        )
        changelog = root / "CHANGELOG.md"
        changelog.write_text(
            f"# Changelog\n\n## {version} - 2026-09-20\n\n### Fixed\n- Example\n",
            encoding="utf-8",
        )
        return PlanInput(
            version=version,
            stable_branch="stable36",
            current_ref="stable36",
            repository=None,
            appinfo=appinfo,
            changelog=changelog,
            milestone=None,
            blocker_queries=(),
        )

    def test_local_plan_is_ready(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.assertTrue(build_plan(self.fixture(directory))["ready"])

    def test_rejects_version_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = replace(self.fixture(directory), version="16.0.1")
            plan = build_plan(config)
            self.assertFalse(plan["ready"])
            self.assertIn("expected '16.0.1'", str(plan["checks"]))

    def test_rejects_wrong_branch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = replace(self.fixture(directory), current_ref="main")
            self.assertFalse(build_plan(config)["ready"])

    def test_rejects_missing_changelog_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = self.fixture(directory)
            config.changelog.write_text("# Changelog\n", encoding="utf-8")
            self.assertFalse(build_plan(config)["ready"])

    @patch("scripts.release_plan._github_json")
    def test_blocks_open_milestone(self, github_json) -> None:
        github_json.return_value = [
            {"title": "16.0.0", "state": "open", "open_issues": 2}
        ]
        with tempfile.TemporaryDirectory() as directory:
            config = replace(
                self.fixture(directory),
                repository="Example/app",
                milestone="16.0.0",
            )
            self.assertFalse(build_plan(config, token="token")["ready"])

    @patch("scripts.release_plan._github_json")
    def test_blocks_matching_open_items(self, github_json) -> None:
        github_json.return_value = {"total_count": 1, "items": [{}]}
        with tempfile.TemporaryDirectory() as directory:
            config = replace(
                self.fixture(directory),
                repository="Example/app",
                blocker_queries=('label:"backport pending"',),
            )
            self.assertFalse(build_plan(config, token="token")["ready"])

    def test_parses_blocker_queries_json(self) -> None:
        self.assertEqual(
            parse_blocker_queries('["label:backport", "is:pr label:blocker"]'),
            ("label:backport", "is:pr label:blocker"),
        )

    def test_rejects_non_array_blocker_queries_json(self) -> None:
        with self.assertRaisesRegex(ValueError, "JSON array of strings"):
            parse_blocker_queries('{"query": "label:backport"}')

    def test_rejects_non_string_blocker_query(self) -> None:
        with self.assertRaisesRegex(ValueError, "JSON array of strings"):
            parse_blocker_queries('["label:backport", 42]')

    def test_rejects_invalid_blocker_queries_json(self) -> None:
        with self.assertRaisesRegex(ValueError, "valid JSON"):
            parse_blocker_queries('["unterminated"')


if __name__ == "__main__":
    unittest.main()
