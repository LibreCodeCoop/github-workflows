# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "actions" / "release-stable-select" / "resolve.py"
SPEC = importlib.util.spec_from_file_location("release_stable_select", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

parse_stable_refs = MODULE.parse_stable_refs
resolve_state = MODULE.resolve_state


class ReleaseStableSelectTest(unittest.TestCase):
    def test_selects_highest_numeric_stable_branch(self) -> None:
        refs = parse_stable_refs(
            "a\trefs/heads/stable9\n"
            "b\trefs/heads/stable35\n"
            "c\trefs/heads/stable100\n"
            "d\trefs/heads/stable34\n"
        )

        state = resolve_state("stable35", refs)

        self.assertEqual(100, state.latest_major)
        self.assertEqual("stable100", state.latest_branch)
        self.assertEqual(35, state.current_major)
        self.assertFalse(state.is_latest)

    def test_current_latest_branch_is_publishable(self) -> None:
        refs = parse_stable_refs(
            "a\trefs/heads/stable33\n"
            "b\trefs/heads/stable34\n"
            "c\trefs/heads/stable35\n"
        )

        state = resolve_state("stable35", refs)

        self.assertEqual(35, state.latest_major)
        self.assertEqual("stable35", state.latest_branch)
        self.assertTrue(state.is_latest)

    def test_ignores_non_exact_stable_names(self) -> None:
        refs = parse_stable_refs(
            "a\trefs/heads/stable35\n"
            "b\trefs/heads/stable36-test\n"
            "c\trefs/heads/stable-next\n"
            "d\trefs/heads/stable035\n"
            "e\trefs/heads/notstable99\n"
        )

        self.assertEqual({35: "stable35"}, refs)

    def test_non_stable_current_branch_never_matches(self) -> None:
        state = resolve_state("main", {35: "stable35"})

        self.assertIsNone(state.current_major)
        self.assertEqual("stable35", state.latest_branch)
        self.assertFalse(state.is_latest)

    def test_no_stable_branch_fails_closed(self) -> None:
        state = resolve_state("stable35", {})

        self.assertEqual(35, state.current_major)
        self.assertIsNone(state.latest_branch)
        self.assertIsNone(state.latest_major)
        self.assertFalse(state.is_latest)


if __name__ == "__main__":
    unittest.main()
