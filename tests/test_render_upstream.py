# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import tempfile
import unittest
from pathlib import Path

from scripts.render_upstream import check, load_templates, sync, write_report


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
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(
            json.dumps(
                {
                    "templates": [
                        {
                            "name": "example",
                            "source": "upstream/vendor/example.yml",
                            "patches": ["patches/example.yml.patch"],
                            "destination": "workflow-templates/example.yml",
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
            report = sync(load_templates(manifest), root)
            rendered = (root / "workflow-templates/example.yml").read_text(encoding="utf-8")
            self.assertIn("name: Patched example", rendered)
            self.assertTrue(report["ok"])
            self.assertEqual(report["updated"], 1)
            self.assertEqual(report["failed"], 0)

    def test_sync_reports_failure_and_continues(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, manifest = self.fixture(directory)

            good_source = root / "upstream/vendor/good.yml"
            good_source.write_text("name: Good\n", encoding="utf-8")

            broken_source = root / "upstream/vendor/broken.yml"
            broken_source.write_text("name: Changed upstream\n", encoding="utf-8")
            broken_patch = root / "patches/broken.yml.patch"
            broken_patch.write_text(
                "--- broken.yml\n"
                "+++ broken.yml\n"
                "@@ -1 +1 @@\n"
                "-name: Old upstream\n"
                "+name: Patched\n",
                encoding="utf-8",
            )

            manifest.write_text(
                json.dumps(
                    {
                        "templates": [
                            {
                                "name": "good",
                                "source": "upstream/vendor/good.yml",
                                "patches": [],
                                "destination": "workflow-templates/good.yml",
                            },
                            {
                                "name": "broken",
                                "source": "upstream/vendor/broken.yml",
                                "patches": ["patches/broken.yml.patch"],
                                "destination": "workflow-templates/broken.yml",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            report = sync(load_templates(manifest), root)

            self.assertFalse(report["ok"])
            self.assertEqual(report["updated"], 1)
            self.assertEqual(report["failed"], 1)
            self.assertEqual(
                (root / "workflow-templates/good.yml").read_text(encoding="utf-8"),
                "name: Good\n",
            )
            self.assertFalse((root / "workflow-templates/broken.yml").exists())
            failed = next(
                item for item in report["templates"] if item["status"] == "failed"
            )
            self.assertEqual(failed["name"], "broken")
            self.assertIn("failed to apply", failed["error"])

    def test_write_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.json"
            report = {
                "ok": False,
                "updated": 1,
                "unchanged": 0,
                "failed": 1,
                "templates": [],
            }
            write_report(report, report_path)
            self.assertEqual(
                json.loads(report_path.read_text(encoding="utf-8")),
                report,
            )

    def test_check_detects_rendered_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, manifest = self.fixture(directory)
            destination = root / "workflow-templates/example.yml"
            destination.parent.mkdir(parents=True)
            destination.write_text("name: stale\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "rendered template is out of date"):
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
                                "destination": "workflow-templates/example.yml",
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
