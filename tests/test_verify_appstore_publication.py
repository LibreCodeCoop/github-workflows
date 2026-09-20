# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

import unittest
from urllib.error import URLError

from scripts.verify_appstore_publication import (
    contains_release,
    normalize_platform,
    normalize_version,
    wait_for_publication,
)


class VerifyAppStorePublicationTest(unittest.TestCase):
    def test_normalizes_version_prefix(self) -> None:
        self.assertEqual(normalize_version("v12.3.4"), "12.3.4")
        self.assertEqual(normalize_version("12.3.4"), "12.3.4")

    def test_normalizes_platform(self) -> None:
        self.assertEqual(normalize_platform("35"), "35.0.0")
        self.assertEqual(normalize_platform("35.1"), "35.1.0")
        self.assertEqual(normalize_platform("35.1.2"), "35.1.2")

    def test_rejects_invalid_platform(self) -> None:
        with self.assertRaises(ValueError):
            normalize_platform("stable35")

    def test_detects_release(self) -> None:
        payload = {
            "data": [
                {
                    "id": "example",
                    "releases": [{"version": "1.2.3"}],
                }
            ]
        }
        self.assertTrue(contains_release(payload, "example", "1.2.3"))
        self.assertFalse(contains_release(payload, "example", "1.2.4"))

    def test_retries_until_release_is_visible(self) -> None:
        responses = iter([
            {"data": [{"id": "example", "releases": []}]},
            {"data": [{"id": "example", "releases": [{"version": "1.2.3"}]}]},
        ])
        sleeps: list[float] = []

        wait_for_publication(
            app_name="example",
            version="v1.2.3",
            platform="35",
            attempts=3,
            delay_seconds=7,
            fetch=lambda _url: next(responses),
            sleep=sleeps.append,
        )

        self.assertEqual(sleeps, [7])

    def test_retries_transient_request_error(self) -> None:
        calls = 0
        sleeps: list[float] = []

        def fetch(_url: str) -> object:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise URLError("temporary")
            return {
                "data": [
                    {
                        "id": "example",
                        "releases": [{"version": "1.2.3"}],
                    }
                ]
            }

        wait_for_publication(
            app_name="example",
            version="1.2.3",
            platform="35.0.0",
            attempts=2,
            delay_seconds=2,
            fetch=fetch,
            sleep=sleeps.append,
        )

        self.assertEqual(sleeps, [2])

    def test_fails_after_attempt_limit_without_extra_sleep(self) -> None:
        sleeps: list[float] = []

        with self.assertRaisesRegex(RuntimeError, "could not be verified"):
            wait_for_publication(
                app_name="example",
                version="1.2.3",
                platform="35",
                attempts=3,
                delay_seconds=5,
                fetch=lambda _url: {"data": []},
                sleep=sleeps.append,
            )

        self.assertEqual(sleeps, [5, 5])


if __name__ == "__main__":
    unittest.main()
