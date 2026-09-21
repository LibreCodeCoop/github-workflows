#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import argparse
import json
import os
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

PERMISSION_RANK = {
    "none": 0,
    "read": 1,
    "triage": 2,
    "write": 3,
    "maintain": 4,
    "admin": 5,
}


def is_authorized(actual: str, minimum: str) -> bool:
    if minimum not in PERMISSION_RANK:
        raise ValueError(f"unsupported minimum permission: {minimum}")
    if actual not in PERMISSION_RANK:
        raise ValueError(f"unsupported repository permission: {actual}")
    return PERMISSION_RANK[actual] >= PERMISSION_RANK[minimum]


def fetch_permission(repository: str, actor: str, token: str, api_url: str = "https://api.github.com") -> str:
    if "/" not in repository:
        raise ValueError("repository must use owner/name form")
    if actor.strip() == "":
        raise ValueError("actor must not be empty")
    if token.strip() == "":
        raise ValueError("GitHub token must not be empty")

    url = f"{api_url.rstrip('/')}/repos/{repository}/collaborators/{quote(actor, safe='')}/permission"
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "LibreCodeCoop/github-workflows",
        },
    )

    try:
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except HTTPError as error:
        if error.code == 404:
            return "none"
        raise RuntimeError(f"GitHub permission lookup failed with HTTP {error.code}") from error

    permission = payload.get("permission") if isinstance(payload, dict) else None
    if not isinstance(permission, str) or permission not in PERMISSION_RANK:
        raise RuntimeError("GitHub returned an invalid repository permission")
    return permission


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--minimum", required=True)
    parser.add_argument("--api-url", default=os.environ.get("GITHUB_API_URL", "https://api.github.com"))
    args = parser.parse_args()

    try:
        actual = fetch_permission(
            args.repository,
            args.actor,
            os.environ.get("GITHUB_TOKEN", ""),
            args.api_url,
        )
        authorized = is_authorized(actual, args.minimum)
    except (RuntimeError, ValueError) as error:
        parser.error(str(error))

    print(json.dumps({
        "actor": args.actor,
        "repository": args.repository,
        "minimum_permission": args.minimum,
        "actual_permission": actual,
        "authorized": authorized,
    }, separators=(",", ":")))

    return 0 if authorized else 3


if __name__ == "__main__":
    raise SystemExit(main())
