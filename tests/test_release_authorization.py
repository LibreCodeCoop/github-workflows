# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_release_authorization.py"

spec = importlib.util.spec_from_file_location("check_release_authorization", SCRIPT)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReleaseAuthorizationTest(unittest.TestCase):
    def test_permission_order_matches_github_levels(self) -> None:
        self.assertTrue(module.is_authorized("admin", "maintain"))
        self.assertTrue(module.is_authorized("maintain", "maintain"))
        self.assertTrue(module.is_authorized("write", "triage"))
        self.assertFalse(module.is_authorized("write", "maintain"))
        self.assertFalse(module.is_authorized("read", "write"))
        self.assertFalse(module.is_authorized("none", "read"))

    def test_rejects_unknown_minimum_permission(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported minimum permission"):
            module.is_authorized("admin", "owner")

    def test_rejects_unknown_actual_permission(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported repository permission"):
            module.is_authorized("custom", "read")

    def test_action_summary_uses_printf_for_markdown_code(self) -> None:
        content = (ROOT / "actions" / "release-authorization" / "action.yml").read_text(encoding="utf-8")
        self.assertIn("printf -- '- Actor: `%s`", content)
        self.assertIn("printf -- '- Required: `%s`", content)
        self.assertIn("printf -- '- Actual: `%s`", content)
        self.assertNotIn('echo "- Actor: `', content)


if __name__ == "__main__":
    unittest.main()
