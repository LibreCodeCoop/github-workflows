#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


FetchJson = Callable[[str], object]
Sleep = Callable[[float], None]


def normalize_version(version: str) -> str:
    return version[1:] if version.startswith("v") else version


def normalize_platform(platform: str) -> str:
    parts = platform.split(".")
    if not all(part.isdigit() for part in parts):
        raise ValueError(f"invalid Nextcloud platform version: {platform!r}")
    if len(parts) > 3:
        raise ValueError(f"invalid Nextcloud platform version: {platform!r}")
    return ".".join(parts + ["0"] * (3 - len(parts)))


def contains_release(payload: object, app_name: str, version: str) -> bool:
    if not isinstance(payload, dict):
        return False

    data = payload.get("data")
    if not isinstance(data, list):
        return False

    for app in data:
        if not isinstance(app, dict) or app.get("id") != app_name:
            continue
        releases = app.get("releases")
        if not isinstance(releases, list):
            continue
        for release in releases:
            if isinstance(release, dict) and release.get("version") == version:
                return True

    return False


def fetch_json(url: str) -> object:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "LibreCodeCoop/github-workflows",
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def wait_for_publication(
    *,
    app_name: str,
    version: str,
    platform: str,
    attempts: int,
    delay_seconds: float,
    fetch: FetchJson = fetch_json,
    sleep: Sleep = time.sleep,
) -> None:
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    if delay_seconds < 0:
        raise ValueError("delay seconds must not be negative")

    normalized_version = normalize_version(version)
    normalized_platform = normalize_platform(platform)
    url = (
        "https://apps.nextcloud.com/api/v1/platform/"
        f"{normalized_platform}/apps.json"
    )

    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            payload = fetch(url)
            last_error = None
            if contains_release(payload, app_name, normalized_version):
                print(
                    f"Verified {app_name} {normalized_version} "
                    "in the Nextcloud App Store"
                )
                return
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            last_error = error

        if attempt == attempts:
            break

        message = (
            f"App Store has not exposed {app_name} {normalized_version} yet "
            f"(attempt {attempt}/{attempts})"
        )
        if last_error is not None:
            message += f": {last_error}"
        print(message)
        sleep(delay_seconds)

    detail = f": {last_error}" if last_error is not None else ""
    raise RuntimeError(
        f"App Store publication could not be verified for "
        f"{app_name} {normalized_version}{detail}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-name", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--attempts", type=int, default=12)
    parser.add_argument("--delay-seconds", type=float, default=10)
    args = parser.parse_args()

    try:
        wait_for_publication(
            app_name=args.app_name,
            version=args.version,
            platform=args.platform,
            attempts=args.attempts,
            delay_seconds=args.delay_seconds,
        )
    except (RuntimeError, ValueError) as error:
        parser.error(str(error))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
