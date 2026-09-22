# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "workflow-templates" / "nightly-release.yml"
CATALOG = ROOT / "workflow-catalog.json"


class NightlyReleaseTemplateTest(unittest.TestCase):
    def test_template_is_published(self) -> None:
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        self.assertIn("nightly-release", catalog["templates"])

    def test_only_latest_exact_stable_can_publish(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")
        sha = "0bac49723213a5aa8e779d365a7b684608cf6989"

        self.assertIn(f"actions/release-stable-select@{sha} # v0.6.0", content)
        self.assertIn("needs.check-latest-stable.outputs.is-latest == 'true'", content)
        self.assertIn("current-branch:", content)
        self.assertIn("latest-branch:", content)
        self.assertIn("latest-major:", content)

    def test_nightly_runs_full_package_and_publication_path(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")

        self.assertIn("make appstore", content)
        self.assertIn("verify-appstore-package", content)
        self.assertIn("integrity:sign-app", content)
        self.assertIn("actions/release-artifact-validate@", content)
        self.assertIn("gh release create nightly", content)
        self.assertIn("nextcloud-libraries/nextcloud-appstore-push-action@", content)
        self.assertIn("nightly: true", content)
        self.assertIn("printf 'Automated nightly build from `%s`.\\n'", content)
        self.assertIn("printf 'Generated from commit `%s`.\\n'", content)
        self.assertNotIn("from `%s`.\\\\\\\\n", content)

    def test_server_is_available_before_makefile_packaging(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")

        server = content.index("- name: Resolve Nextcloud server download")
        package = content.index("- name: Package with Makefile")
        sign = content.index("- name: Sign app")

        self.assertLess(server, package)
        self.assertLess(package, sign)

    def test_release_notes_do_not_emit_literal_newline_escapes(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")

        self.assertNotIn(".\\\\\\\\n'", content)

    def test_checkout_credentials_are_not_persisted(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")

        self.assertNotIn("persist-credentials: true", content)
        self.assertIn("permissions:\n  contents: write", content)
        self.assertNotIn("actions: write", content)

    def test_concurrency_only_cancels_runs_for_the_same_branch(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")

        self.assertIn(
            "group: nightly-release-${{ github.repository }}-${{ github.ref_name }}",
            content,
        )
        self.assertIn("cancel-in-progress: true", content)


if __name__ == "__main__":
    unittest.main()
