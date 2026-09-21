# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "restore_release_artifact.py"

spec = importlib.util.spec_from_file_location("restore_release_artifact", SCRIPT)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RestoreReleaseArtifactTest(unittest.TestCase):
    def test_selects_latest_non_expired_artifact_for_expected_head(self) -> None:
        payload = {"artifacts": [
            {"id": 1, "name": "release-preparation-pr-10", "expired": False, "created_at": "2026-01-01T00:00:00Z", "workflow_run": {"id": 11, "head_sha": "a" * 40}},
            {"id": 3, "name": "release-preparation-pr-10", "expired": False, "created_at": "2026-01-03T00:00:00Z", "workflow_run": {"id": 13, "head_sha": "b" * 40}},
            {"id": 2, "name": "release-preparation-pr-10", "expired": False, "created_at": "2026-01-02T00:00:00Z", "workflow_run": {"id": 12, "head_sha": "a" * 40}},
        ]}
        selected = module.select_artifact(payload, "release-preparation-pr-10", "a" * 40)
        self.assertEqual(2, selected["id"])

    def test_ignores_expired_artifacts(self) -> None:
        payload = {"artifacts": [{"id": 1, "name": "state", "expired": True, "created_at": "2026-01-01T00:00:00Z", "workflow_run": {"head_sha": "a" * 40}}]}
        with self.assertRaisesRegex(RuntimeError, "was not found"):
            module.select_artifact(payload, "state", "a" * 40)

    def test_rejects_path_traversal_archive(self) -> None:
        buffer = io.BytesIO()
        with ZipFile(buffer, "w") as archive:
            archive.writestr("../escape.json", "{}")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "unsafe artifact path"):
                module.safe_extract_zip(buffer.getvalue(), Path(directory))

    def test_extracts_safe_archive(self) -> None:
        buffer = io.BytesIO()
        with ZipFile(buffer, "w") as archive:
            archive.writestr("release-plan.json", "{}")
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            module.safe_extract_zip(buffer.getvalue(), destination)
            self.assertEqual("{}", (destination / "release-plan.json").read_text(encoding="utf-8"))

    def test_validates_originating_workflow(self) -> None:
        module.validate_workflow_run(
            {"event": "workflow_dispatch", "path": ".github/workflows/prepare-release.yml"},
            "workflow_dispatch",
            ".github/workflows/prepare-release.yml",
        )
        with self.assertRaisesRegex(RuntimeError, "does not match"):
            module.validate_workflow_run(
                {"event": "pull_request", "path": ".github/workflows/tests.yml"},
                "workflow_dispatch",
                ".github/workflows/prepare-release.yml",
            )


if __name__ == "__main__":
    unittest.main()
