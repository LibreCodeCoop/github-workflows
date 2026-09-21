# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "sync_release_history.py"

spec = importlib.util.spec_from_file_location("sync_release_history", SCRIPT)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SyncReleaseHistoryTest(unittest.TestCase):
    def test_markdown_release_section_becomes_browsable_rst(self) -> None:
        section = "## 15.1.0 - 2026-09-21\n\n### Added\n- add feature [#10](https://github.com/LibreSign/libresign/pull/10)\n"
        rendered = module.markdown_section_to_rst(section, "15.1.0")
        self.assertIn("15.1.0 - 2026-09-21", rendered)
        self.assertIn("Added\n-----", rendered)
        self.assertIn("`#10 <https://github.com/LibreSign/libresign/pull/10>`_", rendered)
        self.assertIn("SPDX-License-Identifier: AGPL-3.0-or-later", rendered)

    def test_synchronization_requires_successful_matching_publication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepared = root / "prepared.json"
            verification = root / "verification.json"
            prepared.write_text(json.dumps({
                "id": "prepared-1",
                "version": "15.1.0",
                "changelog": {"section": "## 15.1.0 - 2026-09-21\n\n### Fixed\n- fix one\n"},
            }), encoding="utf-8")
            verification.write_text(json.dumps({
                "success": False,
                "prepared_release_id": "prepared-1",
                "github_release": {"published": True},
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not successful"):
                module.synchronize(prepared, verification, root / "docs")

    def test_synchronization_is_idempotent_and_indexes_major(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepared = root / "prepared.json"
            verification = root / "verification.json"
            prepared.write_text(json.dumps({
                "id": "prepared-1",
                "version": "15.1.0",
                "changelog": {"section": "## 15.1.0 - 2026-09-21\n\n### Changed\n- update translations\n"},
            }), encoding="utf-8")
            verification.write_text(json.dumps({
                "success": True,
                "prepared_release_id": "prepared-1",
                "github_release": {"published": True},
            }), encoding="utf-8")
            docs = root / "docs"
            module.synchronize(prepared, verification, docs)
            first = (docs / "developer_manual/release-history/15/15.1.0.rst").read_text(encoding="utf-8")
            module.synchronize(prepared, verification, docs)
            second = (docs / "developer_manual/release-history/15/15.1.0.rst").read_text(encoding="utf-8")
            self.assertEqual(first, second)
            self.assertIn("15.1.0", (docs / "developer_manual/release-history/15/index.rst").read_text(encoding="utf-8"))
            self.assertIn("LibreSign 15 <15/index>", (docs / "developer_manual/release-history/index.rst").read_text(encoding="utf-8"))
            self.assertIn("SPDX-License-Identifier: AGPL-3.0-or-later", (docs / "developer_manual/release-history/15/index.rst").read_text(encoding="utf-8"))

    def test_versions_sort_semantically(self) -> None:
        versions = ["15.9.0", "15.10.0", "15.10.0-rc.1", "15.2.4"]
        rendered = module.render_major_index(15, versions)
        self.assertLess(rendered.index("15.10.0\n"), rendered.index("15.10.0-rc.1\n"))
        self.assertLess(rendered.index("15.10.0-rc.1\n"), rendered.index("15.9.0\n"))


if __name__ == "__main__":
    unittest.main()
