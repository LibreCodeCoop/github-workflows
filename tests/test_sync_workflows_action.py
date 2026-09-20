# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "actions"
    / "sync-workflows"
    / "sync.py"
)
SPEC = importlib.util.spec_from_file_location("sync_workflows_action", MODULE_PATH)
sync_module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(sync_module)


class SyncWorkflowsActionTest(unittest.TestCase):
    def fixture(self) -> tuple[tempfile.TemporaryDirectory, Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        source = root / "source"
        target = root / "target"
        (target / ".github/workflows").mkdir(parents=True)
        source.mkdir()
        return temporary, source, target

    def test_updates_existing_workflow_and_records_catalog_hash(self) -> None:
        temporary, source, target = self.fixture()
        with temporary:
            (source / "lint.yml").write_text("name: New\n", encoding="utf-8")
            (target / ".github/workflows/lint.yml").write_text(
                "name: Old\n", encoding="utf-8"
            )

            report = sync_module.sync(
                source, target, target / ".github/actions-lock.txt"
            )

            self.assertTrue(report["changed"])
            self.assertFalse(report["patch_failed"])
            self.assertEqual(
                (target / ".github/workflows/lint.yml").read_text(encoding="utf-8"),
                "name: New\n",
            )
            expected = hashlib.md5(
                b"name: New\n", usedforsecurity=False
            ).hexdigest()
            self.assertEqual(
                sync_module.parse_lock(target / ".github/actions-lock.txt")["lint.yml"],
                expected,
            )

    def test_skips_workflow_not_installed_in_consumer(self) -> None:
        temporary, source, target = self.fixture()
        with temporary:
            (source / "unused.yml").write_text("name: Unused\n", encoding="utf-8")

            report = sync_module.sync(
                source, target, target / ".github/actions-lock.txt"
            )

            self.assertFalse(report["changed"])
            self.assertEqual(report["skipped"], ["unused.yml"])

    def test_reports_unchanged_when_lock_matches_catalog(self) -> None:
        temporary, source, target = self.fixture()
        with temporary:
            content = "name: Same\n"
            source_file = source / "lint.yml"
            source_file.write_text(content, encoding="utf-8")
            (target / ".github/workflows/lint.yml").write_text(
                content, encoding="utf-8"
            )
            digest = sync_module.md5(source_file)
            sync_module.write_lock(
                target / ".github/actions-lock.txt", {"lint.yml": digest}
            )

            report = sync_module.sync(
                source, target, target / ".github/actions-lock.txt"
            )

            self.assertFalse(report["changed"])
            self.assertEqual(report["unchanged"], ["lint.yml"])

    def test_applies_consumer_local_patch(self) -> None:
        temporary, source, target = self.fixture()
        with temporary:
            source_file = source / "sync.yml"
            source_file.write_text(
                "branches:\n  - default\n", encoding="utf-8"
            )
            target_file = target / ".github/workflows/sync.yml"
            target_file.write_text("old\n", encoding="utf-8")
            patch_file = target / ".github/workflows/sync.yml.patch"
            patch_file.write_text(
                "--- a/.github/workflows/sync.yml\n"
                "+++ b/.github/workflows/sync.yml\n"
                "@@ -1,2 +1,3 @@\n"
                " branches:\n"
                "   - default\n"
                "+  - stable32\n",
                encoding="utf-8",
            )

            report = sync_module.sync(
                source, target, target / ".github/actions-lock.txt"
            )

            self.assertFalse(report["patch_failed"])
            self.assertEqual(
                target_file.read_text(encoding="utf-8"),
                "branches:\n  - default\n  - stable32\n",
            )
            self.assertEqual(
                sync_module.parse_lock(target / ".github/actions-lock.txt")["sync.yml"],
                sync_module.md5(source_file),
            )

    def test_broken_patch_sets_draft_signal_and_keeps_catalog_lock(self) -> None:
        temporary, source, target = self.fixture()
        with temporary:
            source_file = source / "sync.yml"
            source_file.write_text("name: New\n", encoding="utf-8")
            target_file = target / ".github/workflows/sync.yml"
            target_file.write_text("name: Old\n", encoding="utf-8")
            patch_file = target / ".github/workflows/sync.yml.patch"
            patch_file.write_text(
                "--- a/.github/workflows/sync.yml\n"
                "+++ b/.github/workflows/sync.yml\n"
                "@@ -1 +1 @@\n"
                "-name: Missing\n"
                "+name: Patched\n",
                encoding="utf-8",
            )

            report = sync_module.sync(
                source, target, target / ".github/actions-lock.txt"
            )

            self.assertTrue(report["changed"])
            self.assertTrue(report["patch_failed"])
            self.assertEqual(report["failed"], ["sync.yml"])
            self.assertEqual(
                sync_module.parse_lock(target / ".github/actions-lock.txt")["sync.yml"],
                sync_module.md5(source_file),
            )

    def test_mixed_result_summary_is_deterministic(self) -> None:
        summary = sync_module.render_summary(
            {
                "updated": ["a.yml"],
                "unchanged": ["b.yml"],
                "skipped": ["c.yml"],
                "failed": ["a.yml"],
                "details": ["- a.yml: Patch failed"],
            }
        )

        self.assertIn("- Updated: 1", summary)
        self.assertIn("- Unchanged: 1", summary)
        self.assertIn("- Skipped: 1", summary)
        self.assertIn("- Patch failures: 1", summary)
        self.assertIn("- a.yml: Patch failed", summary)


if __name__ == "__main__":
    unittest.main()
