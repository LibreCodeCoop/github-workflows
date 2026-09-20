# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.sync_consumer import (
    LOCK_HEADER,
    load_consumers,
    matrix,
    parse_lock,
    render_pull_request_body,
    sha256,
    sync_consumer,
)


class SyncConsumerTest(unittest.TestCase):
    def create_source(self, root: Path, content: str = "name: REUSE\n") -> Path:
        source = root / "source"
        source.mkdir(parents=True)
        (source / "reuse.yml").write_text(content, encoding="utf-8")
        return source

    def target_workflow(self, root: Path) -> Path:
        return root / "target/.github/workflows/reuse.yml"

    def lock_path(self, root: Path) -> Path:
        return root / "target/.github/librecode-workflows.lock"

    def test_load_consumers_and_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "consumers.json"
            manifest.write_text(
                json.dumps(
                    {
                        "consumers": [
                            {
                                "repository": "LibreCodeCoop/extract",
                                "workflows": ["reuse.yml"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            consumers = load_consumers(manifest)

            self.assertEqual(consumers[0].repository, "LibreCodeCoop/extract")
            self.assertEqual(consumers[0].workflows, ("reuse.yml",))
            self.assertEqual(
                matrix(consumers),
                {
                    "include": [
                        {
                            "repository": "LibreCodeCoop/extract",
                            "workflows": ["reuse.yml"],
                        }
                    ]
                },
            )

    def test_adopts_matching_existing_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.create_source(root)
            target = self.target_workflow(root)
            target.parent.mkdir(parents=True)
            target.write_bytes((source / "reuse.yml").read_bytes())

            report = sync_consumer(
                source,
                root / "target",
                ("reuse.yml",),
                self.lock_path(root),
            )

            self.assertTrue(report["ok"])
            self.assertEqual(report["results"][0]["status"], "adopted")
            lock = parse_lock(self.lock_path(root))
            self.assertEqual(lock["reuse.yml"], sha256(source / "reuse.yml"))

    def test_refuses_to_adopt_different_existing_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.create_source(root)
            target = self.target_workflow(root)
            target.parent.mkdir(parents=True)
            target.write_text("name: Local\n", encoding="utf-8")

            report = sync_consumer(
                source,
                root / "target",
                ("reuse.yml",),
                self.lock_path(root),
            )

            self.assertFalse(report["ok"])
            self.assertEqual(report["results"][0]["status"], "failed")
            self.assertEqual(target.read_text(encoding="utf-8"), "name: Local\n")

    def test_updates_when_target_matches_lock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.create_source(root, "name: New\n")
            target = self.target_workflow(root)
            target.parent.mkdir(parents=True)
            target.write_text("name: Old\n", encoding="utf-8")
            old_hash = hashlib.sha256(b"name: Old\n").hexdigest()
            lock = self.lock_path(root)
            lock.parent.mkdir(parents=True, exist_ok=True)
            lock.write_text(
                LOCK_HEADER + "\n" + f"{old_hash} reuse.yml\n",
                encoding="utf-8",
            )

            report = sync_consumer(
                source,
                root / "target",
                ("reuse.yml",),
                lock,
            )

            self.assertTrue(report["ok"])
            self.assertEqual(report["results"][0]["status"], "updated")
            self.assertEqual(target.read_text(encoding="utf-8"), "name: New\n")
            self.assertEqual(parse_lock(lock)["reuse.yml"], sha256(source / "reuse.yml"))

    def test_refuses_local_divergence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.create_source(root, "name: New\n")
            target = self.target_workflow(root)
            target.parent.mkdir(parents=True)
            target.write_text("name: Local\n", encoding="utf-8")
            old_hash = hashlib.sha256(b"name: Old\n").hexdigest()
            lock = self.lock_path(root)
            lock.parent.mkdir(parents=True, exist_ok=True)
            lock.write_text(
                LOCK_HEADER + "\n" + f"{old_hash} reuse.yml\n",
                encoding="utf-8",
            )

            report = sync_consumer(
                source,
                root / "target",
                ("reuse.yml",),
                lock,
            )

            self.assertFalse(report["ok"])
            self.assertEqual(report["results"][0]["status"], "failed")
            self.assertEqual(target.read_text(encoding="utf-8"), "name: Local\n")
            self.assertEqual(parse_lock(lock)["reuse.yml"], old_hash)

    def test_reports_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.create_source(root)
            target = self.target_workflow(root)
            target.parent.mkdir(parents=True)
            target.write_bytes((source / "reuse.yml").read_bytes())
            digest = sha256(source / "reuse.yml")
            lock = self.lock_path(root)
            lock.parent.mkdir(parents=True, exist_ok=True)
            lock.write_text(
                LOCK_HEADER + "\n" + f"{digest} reuse.yml\n",
                encoding="utf-8",
            )

            report = sync_consumer(
                source,
                root / "target",
                ("reuse.yml",),
                lock,
            )

            self.assertTrue(report["ok"])
            self.assertEqual(report["results"][0]["status"], "unchanged")

    def test_pull_request_body_explains_divergence_protection(self) -> None:
        body = render_pull_request_body(
            "LibreCodeCoop/extract",
            {
                "ok": True,
                "results": [
                    {
                        "workflow": "reuse.yml",
                        "status": "updated",
                        "message": "workflow updated to the current template",
                    }
                ],
            },
        )

        self.assertIn("LibreCodeCoop/extract", body)
        self.assertIn("SHA-256", body)
        self.assertIn("never overwritten silently", body)


if __name__ == "__main__":
    unittest.main()
