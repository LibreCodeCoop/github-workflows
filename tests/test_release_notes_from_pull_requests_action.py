# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "actions" / "release-notes-from-pull-requests" / "generate.py"

spec = importlib.util.spec_from_file_location(
    "release_notes_from_pull_requests",
    SCRIPT,
)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FakeApi:
    def __init__(self, responses: dict[str, list[dict[str, Any]]]) -> None:
        self.responses = responses
        self.urls: list[str] = []

    def __call__(self, url: str, token: str) -> Any:
        self.urls.append(url)
        sha = url.split("/commits/", 1)[1].split("/pulls", 1)[0]
        return self.responses.get(sha, [])


class ReleaseNotesFromPullRequestsTest(unittest.TestCase):
    def test_prefers_merged_pr_for_requested_base_branch(self) -> None:
        pull_requests = [
            {
                "number": 20,
                "title": "Wrong branch",
                "merged_at": "2026-09-01T00:00:00Z",
                "base": {"ref": "stable34"},
            },
            {
                "number": 30,
                "title": "Right branch",
                "merged_at": "2026-09-02T00:00:00Z",
                "base": {"ref": "stable35"},
            },
        ]
        selected = module.choose_pull_request(pull_requests, "stable35")
        self.assertEqual(selected["number"], 30)

    def test_ignores_unmerged_pull_requests(self) -> None:
        selected = module.choose_pull_request(
            [
                {
                    "number": 12,
                    "title": "Still open",
                    "merged_at": None,
                    "base": {"ref": "stable35"},
                }
            ],
            "stable35",
        )
        self.assertIsNone(selected)

    def test_deduplicates_pull_request_across_multiple_commits(self) -> None:
        api = FakeApi(
            {
                "a" * 40: [
                    {
                        "number": 50,
                        "title": "Feature",
                        "merged_at": "2026-09-01T00:00:00Z",
                        "base": {"ref": "stable35"},
                    }
                ],
                "b" * 40: [
                    {
                        "number": 50,
                        "title": "Feature",
                        "merged_at": "2026-09-01T00:00:00Z",
                        "base": {"ref": "stable35"},
                    }
                ],
            }
        )
        lines, prs, fallbacks = module.generate_changes(
            commits=["a" * 40, "b" * 40],
            repository="LibreSign/libresign",
            branch="stable35",
            server_url="https://github.com",
            api_url="https://api.github.com",
            token="token",
            subject_lookup=lambda sha: "unused",
            request=api,
        )
        self.assertEqual(
            lines,
            [
                "- Feature ([#50](https://github.com/LibreSign/libresign/pull/50))"
            ],
        )
        self.assertEqual(prs, 1)
        self.assertEqual(fallbacks, 0)

    def test_direct_commit_is_kept_as_fallback(self) -> None:
        sha = "abcdef0123456789abcdef0123456789abcdef01"
        api = FakeApi({})
        lines, prs, fallbacks = module.generate_changes(
            commits=[sha],
            repository="LibreSign/libresign",
            branch="stable35",
            server_url="https://github.com",
            api_url="https://api.github.com",
            token="token",
            subject_lookup=lambda value: "Direct maintenance commit",
            request=api,
        )
        self.assertEqual(
            lines,
            ["- Direct maintenance commit (`abcdef0`)"],
        )
        self.assertEqual(prs, 0)
        self.assertEqual(fallbacks, 1)

    def test_titles_are_sanitized_before_markdown_rendering(self) -> None:
        sha = "c" * 40
        api = FakeApi(
            {
                sha: [
                    {
                        "number": 77,
                        "title": "First *line*\n@maintainers [link](https://evil.example)",
                        "merged_at": "2026-09-01T00:00:00Z",
                        "base": {"ref": "stable35"},
                    }
                ]
            }
        )
        lines, _, _ = module.generate_changes(
            commits=[sha],
            repository="acme/app",
            branch="stable35",
            server_url="https://git.example",
            api_url="https://git.example/api/v3",
            token="token",
            subject_lookup=lambda value: "unused",
            request=api,
        )
        self.assertEqual(
            lines,
            [
                "- First \\*line\\* @\u200bmaintainers "
                "\\[link\\](https://evil.example) "
                "([#77](https://git.example/acme/app/pull/77))"
            ],
        )

    def test_direct_commit_subject_is_sanitized(self) -> None:
        sha = "e" * 40
        api = FakeApi({})
        lines, _, _ = module.generate_changes(
            commits=[sha],
            repository="acme/app",
            branch="stable35",
            server_url="https://github.com",
            api_url="https://api.github.com",
            token="token",
            subject_lookup=lambda value: module.sanitize_markdown_text(
                "Fix *all* @maintainers"
            ),
            request=api,
        )
        self.assertEqual(
            lines,
            ["- Fix \\*all\\* @\u200bmaintainers (`eeeeeee`)"],
        )

    def test_api_url_supports_github_enterprise(self) -> None:
        sha = "d" * 40
        api = FakeApi({})
        module.generate_changes(
            commits=[sha],
            repository="acme/app",
            branch="stable35",
            server_url="https://git.example",
            api_url="https://git.example/api/v3",
            token="token",
            subject_lookup=lambda value: "Commit",
            request=api,
        )
        self.assertEqual(
            api.urls,
            [f"https://git.example/api/v3/repos/acme/app/commits/{sha}/pulls"],
        )

    def test_authorization_header_is_not_forwarded_on_redirect(self) -> None:
        request = module.build_api_request(
            "https://api.github.com/repos/acme/app/commits/abc/pulls",
            "secret-token",
        )
        self.assertNotIn("Authorization", request.headers)
        self.assertEqual(
            request.unredirected_hdrs["Authorization"],
            "Bearer secret-token",
        )

    def test_action_contract_is_generic(self) -> None:
        content = (
            ROOT / "actions" / "release-notes-from-pull-requests" / "action.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("from-ref:", content)
        self.assertIn("to-ref:", content)
        self.assertIn("branch:", content)
        self.assertNotIn("nightly", content.lower())
        self.assertNotIn("nextcloud", content.lower())


if __name__ == "__main__":
    unittest.main()
