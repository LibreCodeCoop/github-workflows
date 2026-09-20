# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import tempfile
import unittest
from pathlib import Path

from scripts.render_upstream import check, load_templates, sync


class RenderUpstreamTest(unittest.TestCase):
    def fixture(self, directory: str) -> tuple[Path, Path]:
        root = Path(directory)
        source = root / "upstream/vendor/example.yml"
        source.parent.mkdir(parents=True)
        source.write_text(
            "name: Example\n\njobs:\n  test:\n    runs-on: ubuntu-latest\n",
            encoding="utf-8",
        )

        patch = root / "patches/example.yml.patch"
        patch.parent.mkdir(parents=True)
        patch.write_text(
            "--- example.yml\n"
            "+++ example.yml\n"
            "@@ -1,5 +1,5 @@\n"
            "-name: Example\n"
            "+name: Patched example\n"
            " \n"
            " jobs:\n"
            "   test:\n"
            "     runs-on: ubuntu-latest\n",
            encoding="utf-8",
        )

        manifest = root / "upstream/templates.json"
        manifest.write_text(
            json.dumps(
                {
                    "templates": [
                        {
                            "name": "example",
                            "source": "upstream/vendor/example.yml",
                            "patches": ["patches/example.yml.patch"],
                            "destination": "templates/example.yml",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return root, manifest

    def test_sync_applies_patch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, manifest = self.fixture(directory)
            sync(load_templates(manifest), root)
            rendered = (root / "templates/example.yml").read_text(encoding="utf-8")
            self.assertIn("name: Patched example", rendered)

    def test_check_detects_rendered_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, manifest = self.fixture(directory)
            destination = root / "templates/example.yml"
            destination.parent.mkdir(parents=True)
            destination.write_text("name: stale\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "rendered templates are out of date"):
                check(load_templates(manifest), root)

    def test_rejects_unsafe_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "templates.json"
            manifest.write_text(
                json.dumps(
                    {
                        "templates": [
                            {
                                "name": "example",
                                "source": "../example.yml",
                                "patches": [],
                                "destination": "templates/example.yml",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "unsafe path"):
                load_templates(manifest)


if __name__ == "__main__":
    unittest.main()
