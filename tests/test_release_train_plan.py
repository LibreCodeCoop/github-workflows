# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.release_train_plan import (
    _parse_appinfo,
    _parse_branches,
    _propose_version,
    build_release_train,
    render_summary,
)


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return result.stdout.strip()


class ReleaseTrainPlanTest(unittest.TestCase):
    def init_repo(self, directory: str) -> Path:
        repo = Path(directory)
        git(repo, "init", "-b", "main")
        git(repo, "config", "user.email", "test@example.com")
        git(repo, "config", "user.name", "Test")
        return repo

    def write_appinfo(self, repo: Path, version: str, nc: int) -> None:
        appinfo = repo / "appinfo/info.xml"
        appinfo.parent.mkdir(parents=True, exist_ok=True)
        appinfo.write_text(
            "<info>"
            f"<version>{version}</version>"
            "<dependencies>"
            f'<nextcloud min-version="{nc}" max-version="{nc}" />'
            "</dependencies>"
            "</info>",
            encoding="utf-8",
        )

    def commit_release_line(self, repo: Path, branch: str, version: str, nc: int) -> None:
        git(repo, "checkout", "-B", branch)
        self.write_appinfo(repo, version, nc)
        git(repo, "add", "appinfo/info.xml")
        git(repo, "commit", "-m", f"chore: prepare {branch} {version}")

    def commit_change(self, repo: Path, message: str, filename: str = "change.txt") -> None:
        path = repo / filename
        path.write_text(message + "\n", encoding="utf-8")
        git(repo, "add", filename)
        git(repo, "commit", "-m", message)

    def test_orders_stable_lines_oldest_first(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.init_repo(directory)
            self.commit_release_line(repo, "stable35", "15.2.3", 35)
            git(repo, "tag", "v15.2.3")
            self.commit_release_line(repo, "stable34", "14.4.8", 34)
            git(repo, "tag", "v14.4.8")

            plan = build_release_train(
                repo,
                ("stable35", "stable34"),
                {},
            )

            self.assertTrue(plan["ready"])
            self.assertEqual(
                plan["publication_order"],
                ["stable34", "stable35"],
            )
            self.assertEqual(
                plan["releases"][0]["proposed_version"],
                "14.4.9",
            )
            self.assertEqual(plan["releases"][0]["release_kind"], "patch")
            self.assertEqual(
                plan["releases"][1]["milestone"],
                "Next Patch (35)",
            )

    def test_feature_commit_proposes_minor_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.init_repo(directory)
            self.commit_release_line(repo, "stable35", "15.2.3", 35)
            git(repo, "tag", "v15.2.3")
            self.commit_change(repo, "feat: add signing policy")

            plan = build_release_train(repo, ("stable35",), {})

            release = plan["releases"][0]
            self.assertEqual(release["release_kind"], "minor")
            self.assertEqual(release["proposed_version"], "15.3.0")
            self.assertIn("feat", release["conventional_types"])

    def test_fix_commit_proposes_patch_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.init_repo(directory)
            self.commit_release_line(repo, "stable35", "15.2.3", 35)
            git(repo, "tag", "v15.2.3")
            self.commit_change(repo, "fix: handle empty signature")

            plan = build_release_train(repo, ("stable35",), {})

            release = plan["releases"][0]
            self.assertEqual(release["release_kind"], "patch")
            self.assertEqual(release["proposed_version"], "15.2.4")

    def test_first_release_of_new_line_uses_declared_major_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.init_repo(directory)
            self.commit_release_line(repo, "stable36", "16.0.0", 36)

            plan = build_release_train(repo, ("stable36",), {})

            release = plan["releases"][0]
            self.assertEqual(release["release_kind"], "major")
            self.assertEqual(release["previous_tag"], None)
            self.assertEqual(release["proposed_version"], "16.0.0")

    def test_breaking_marker_does_not_auto_increment_major(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.init_repo(directory)
            self.commit_release_line(repo, "stable35", "15.2.3", 35)
            git(repo, "tag", "v15.2.3")
            self.commit_change(repo, "feat!: replace signing workflow")

            plan = build_release_train(repo, ("stable35",), {})

            release = plan["releases"][0]
            self.assertEqual(release["release_kind"], "minor")
            self.assertEqual(release["proposed_version"], "15.3.0")
            self.assertTrue(any("breaking" in item for item in release["warnings"]))

    def test_explicit_version_override_is_visible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.init_repo(directory)
            self.commit_release_line(repo, "stable35", "15.2.3", 35)
            git(repo, "tag", "v15.2.3")

            plan = build_release_train(
                repo,
                ("stable35",),
                {"stable35": "15.3.0"},
            )

            release = plan["releases"][0]
            self.assertEqual(release["proposed_version"], "15.2.4")
            self.assertEqual(release["requested_version"], "15.3.0")
            self.assertIn("version override selected", release["warnings"][0])

    def test_translation_commit_remains_patch_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.init_repo(directory)
            self.commit_release_line(repo, "stable35", "15.2.3", 35)
            git(repo, "tag", "v15.2.3")
            self.commit_change(repo, "fix(l10n): Update translations from Transifex")

            plan = build_release_train(repo, ("stable35",), {})

            release = plan["releases"][0]
            self.assertEqual(release["release_kind"], "patch")
            self.assertEqual(release["proposed_version"], "15.2.4")

    def test_dependency_bump_remains_patch_even_if_dependency_major_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.init_repo(directory)
            self.commit_release_line(repo, "stable35", "15.2.3", 35)
            git(repo, "tag", "v15.2.3")
            self.commit_change(
                repo,
                "chore(deps-dev): Bump example/library from 1.0.0 to 2.0.0",
            )

            plan = build_release_train(repo, ("stable35",), {})

            release = plan["releases"][0]
            self.assertEqual(release["release_kind"], "patch")
            self.assertEqual(release["proposed_version"], "15.2.4")

    def test_existing_tag_blocks_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.init_repo(directory)
            self.commit_release_line(repo, "stable35", "15.2.3", 35)
            git(repo, "tag", "v15.2.3")
            git(repo, "tag", "v15.2.4")

            plan = build_release_train(
                repo,
                ("stable35",),
                {"stable35": "15.2.4"},
            )

            self.assertFalse(plan["ready"])
            self.assertIn(
                "tag v15.2.4 already exists",
                plan["releases"][0]["blockers"],
            )

    def test_branch_nextcloud_major_mismatch_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.init_repo(directory)
            self.commit_release_line(repo, "stable35", "15.2.3", 34)

            plan = build_release_train(repo, ("stable35",), {})

            self.assertFalse(plan["ready"])
            self.assertIn(
                "stable35 implies Nextcloud 35 but appinfo declares 34",
                plan["releases"][0]["blockers"],
            )

    def test_missing_branch_is_reported_not_crashed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.init_repo(directory)
            plan = build_release_train(repo, ("stable99",), {})
            self.assertFalse(plan["ready"])
            self.assertIn("does not exist", plan["releases"][0]["blockers"][0])

    def test_rejects_duplicate_branches(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicates"):
            _parse_branches('["stable34","stable34"]')

    def test_parses_libresign_style_appinfo(self) -> None:
        version, major = _parse_appinfo(
            '<info><version>15.2.3</version><dependencies>'
            '<nextcloud min-version="35" max-version="35" />'
            '</dependencies></info>'
        )
        self.assertEqual(version, "15.2.3")
        self.assertEqual(major, 35)

    def test_summary_contains_publication_order_rows(self) -> None:
        summary = render_summary(
            {
                "ready": True,
                "publication_order": ["stable34"],
                "releases": [
                    {
                        "branch": "stable34",
                        "head_sha": "abc",
                        "current_version": "14.4.8",
                        "nextcloud_major": 34,
                        "previous_tag": "v14.4.8",
                        "release_kind": "patch",
                        "conventional_types": ["fix"],
                        "proposed_version": "14.4.9",
                        "requested_version": "14.4.9",
                        "milestone": "Next Patch (34)",
                        "ready": True,
                        "blockers": [],
                        "warnings": [],
                    }
                ],
            }
        )
        self.assertIn("| stable34 | 14.4.8 | v14.4.8 | patch |", summary)


if __name__ == "__main__":
    unittest.main()
