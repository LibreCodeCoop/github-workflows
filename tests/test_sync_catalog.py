# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import tempfile
import unittest
from pathlib import Path

from scripts.sync_catalog import (
    check_catalog,
    collect_publishable,
    load_catalog_manifest,
    sync_catalog,
)


class SyncCatalogTest(unittest.TestCase):
    def write_template(
        self,
        directory: Path,
        name: str = "reuse",
        *,
        icon_name: str = "octicon verified",
    ) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{name}.yml").write_text(
            "name: Example\n",
            encoding="utf-8",
        )
        (directory / f"{name}.properties.json").write_text(
            json.dumps(
                {
                    "name": "Example",
                    "description": "Example workflow",
                    "iconName": icon_name,
                }
            )
            + "\n",
            encoding="utf-8",
        )

    def test_sync_adds_updates_and_removes_managed_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            target = root / "target"
            self.write_template(source)

            target.mkdir()
            (target / "reuse.yml").write_text("name: Old\n", encoding="utf-8")
            (target / "old.yml").write_text("name: Old\n", encoding="utf-8")
            (target / "old.properties.json").write_text("{}\n", encoding="utf-8")
            (target / "README.md").write_text("keep me\n", encoding="utf-8")

            report = sync_catalog(source, target)

            self.assertEqual(report["updated"], ["reuse.properties.json", "reuse.yml"])
            self.assertEqual(report["removed"], ["old.properties.json", "old.yml"])
            self.assertTrue((target / "README.md").is_file())
            check_catalog(source, target)

    def test_sync_reports_unchanged_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            target = root / "target"
            self.write_template(source)
            sync_catalog(source, target)

            report = sync_catalog(source, target)

            self.assertEqual(report["updated"], [])
            self.assertEqual(
                report["unchanged"],
                ["reuse.properties.json", "reuse.yml"],
            )
            self.assertEqual(report["removed"], [])

    def test_requires_metadata_for_each_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / "reuse.yml").write_text("name: Example\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "missing template metadata"):
                collect_publishable(source)

    def test_rejects_metadata_without_matching_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / "reuse.properties.json").write_text(
                '{"name":"Example"}\n',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "no matching workflow"):
                collect_publishable(source)

    def test_requires_custom_svg_icon(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            self.write_template(source, icon_name="custom-icon")

            with self.assertRaisesRegex(ValueError, "missing icon custom-icon.svg"):
                collect_publishable(source)

            (source / "custom-icon.svg").write_text(
                "<svg></svg>\n",
                encoding="utf-8",
            )
            collect_publishable(source)

    def test_invalid_source_does_not_partially_modify_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            target = root / "target"
            self.write_template(source)
            target.mkdir()
            existing = target / "reuse.yml"
            existing.write_text("name: Published\n", encoding="utf-8")

            (source / "reuse.properties.json").unlink()

            with self.assertRaisesRegex(ValueError, "missing template metadata"):
                sync_catalog(source, target)

            self.assertEqual(
                existing.read_text(encoding="utf-8"),
                "name: Published\n",
            )

    def test_manifest_limits_catalog_to_approved_templates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            target = root / "target"
            self.write_template(source, "reuse")
            self.write_template(source, "sensitive")

            target.mkdir()
            (target / "sensitive.yml").write_text(
                "name: Published by mistake\n",
                encoding="utf-8",
            )
            (target / "sensitive.properties.json").write_text(
                '{"name":"Sensitive"}\n',
                encoding="utf-8",
            )

            report = sync_catalog(source, target, ("reuse",))

            self.assertTrue((target / "reuse.yml").is_file())
            self.assertTrue((target / "reuse.properties.json").is_file())
            self.assertFalse((target / "sensitive.yml").exists())
            self.assertFalse((target / "sensitive.properties.json").exists())
            self.assertEqual(
                report["removed"],
                ["sensitive.properties.json", "sensitive.yml"],
            )

    def test_load_catalog_manifest_rejects_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "workflow-catalog.json"
            manifest.write_text(
                '{"templates":["reuse","reuse"]}\n',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "duplicate template"):
                load_catalog_manifest(manifest)

    def test_manifest_requires_declared_template_to_exist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            self.write_template(source, "reuse")

            with self.assertRaisesRegex(
                ValueError,
                "exactly one workflow file: missing",
            ):
                collect_publishable(source, ("reuse", "missing"))

    def test_check_detects_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            target = root / "target"
            self.write_template(source)
            sync_catalog(source, target)
            (target / "reuse.yml").write_text("name: Drift\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "catalog file differs"):
                check_catalog(source, target)


if __name__ == "__main__":
    unittest.main()
