# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.sync_upstream import Source, check, load_sources, sync


class SyncUpstreamTest(unittest.TestCase):
    def test_loads_valid_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "sources.json"
            manifest.write_text(
                json.dumps(
                    {
                        "sources": [
                            {
                                "name": "workflow",
                                "url": "https://raw.githubusercontent.com/example/project/0123456789012345678901234567890123456789/workflow.yml",
                                "sha256": "a" * 64,
                                "destination": "templates/workflow.yml",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            [source] = load_sources(manifest)
            self.assertEqual(source.name, "workflow")
            self.assertEqual(source.destination, Path("templates/workflow.yml"))

    def test_rejects_invalid_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "sources.json"
            manifest.write_text(
                json.dumps(
                    {
                        "sources": [
                            {
                                "name": "workflow",
                                "url": "https://example.invalid/commit/workflow.yml",
                                "sha256": "not-a-hash",
                                "destination": "templates/workflow.yml",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "sha256"):
                load_sources(manifest)

    def test_sync_writes_verified_content(self) -> None:
        content = b"name: Example\n"
        source = Source(
            name="workflow",
            url="https://example.invalid/workflow.yml",
            sha256=hashlib.sha256(content).hexdigest(),
            destination=Path("templates/workflow.yml"),
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("scripts.sync_upstream.fetch", return_value=content):
                sync([source], root)

            self.assertEqual(
                (root / "templates/workflow.yml").read_bytes(),
                content,
            )

    def test_check_detects_drift(self) -> None:
        expected = b"name: Expected\n"
        source = Source(
            name="workflow",
            url="https://example.invalid/workflow.yml",
            sha256=hashlib.sha256(expected).hexdigest(),
            destination=Path("templates/workflow.yml"),
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "templates").mkdir()
            (root / "templates/workflow.yml").write_bytes(b"name: Old\n")

            with patch("scripts.sync_upstream.fetch", return_value=expected):
                with self.assertRaisesRegex(ValueError, "out of date"):
                    check([source], root)

    def test_rejects_destination_escape(self) -> None:
        content = b"name: Example\n"
        source = Source(
            name="workflow",
            url="https://example.invalid/workflow.yml",
            sha256=hashlib.sha256(content).hexdigest(),
            destination=Path("../outside.yml"),
        )

        with tempfile.TemporaryDirectory() as directory:
            with patch("scripts.sync_upstream.fetch", return_value=content):
                with self.assertRaisesRegex(ValueError, "unsafe destination"):
                    sync([source], Path(directory))


if __name__ == "__main__":
    unittest.main()
