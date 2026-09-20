#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.etree import ElementTree


SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


@dataclass(frozen=True)
class PlanInput:
    version: str
    stable_branch: str
    current_ref: str
    repository: str | None
    appinfo: Path
    changelog: Path
    milestone: str | None
    blocker_queries: tuple[str, ...]


def build_plan(config: PlanInput, token: str | None = None) -> dict[str, object]:
    checks: list[dict[str, object]] = [
        _check_version(config.version),
        _check_branch(config.stable_branch, config.current_ref),
        _check_appinfo(config.appinfo, config.version),
        _check_changelog(config.changelog, config.version),
    ]

    if config.milestone:
        checks.append(
            _check_milestone(
                repository=_required(config.repository, "repository"),
                milestone=config.milestone,
                token=_required(token, "GitHub token"),
            )
        )

    for query in config.blocker_queries:
        checks.append(
            _check_blocker_query(
                repository=_required(config.repository, "repository"),
                query=query,
                token=_required(token, "GitHub token"),
            )
        )

    return {
        "version": config.version,
        "stable_branch": config.stable_branch,
        "repository": config.repository,
        "ready": all(bool(check["ok"]) for check in checks),
        "checks": checks,
    }


def _check_version(version: str) -> dict[str, object]:
    return _result(
        "version",
        bool(SEMVER.fullmatch(version)),
        f"release version is {version}",
        "version must use MAJOR.MINOR.PATCH",
    )


def _check_branch(stable_branch: str, current_ref: str) -> dict[str, object]:
    return _result(
        "branch",
        current_ref == stable_branch,
        f"current ref matches stable branch {stable_branch}",
        f"current ref {current_ref!r} does not match stable branch {stable_branch!r}",
    )


def _check_appinfo(path: Path, version: str) -> dict[str, object]:
    if not path.is_file():
        return _result("appinfo", False, "", f"{path} does not exist")

    try:
        root = ElementTree.parse(path).getroot()
    except (ElementTree.ParseError, OSError) as error:
        return _result("appinfo", False, "", f"cannot parse {path}: {error}")

    declared = root.findtext("version")
    return _result(
        "appinfo",
        declared == version,
        f"{path} declares version {version}",
        f"{path} declares version {declared!r}, expected {version!r}",
    )


def _check_changelog(path: Path, version: str) -> dict[str, object]:
    if not path.is_file():
        return _result("changelog", False, "", f"{path} does not exist")

    content = path.read_text(encoding="utf-8")
    pattern = re.compile(rf"^##\s+{re.escape(version)}(?:\s+-\s+.+)?\s*$", re.MULTILINE)
    return _result(
        "changelog",
        bool(pattern.search(content)),
        f"{path} contains a section for {version}",
        f"{path} does not contain a level-2 section for {version}",
    )


def _check_milestone(repository: str, milestone: str, token: str) -> dict[str, object]:
    owner, name = _split_repository(repository)
    milestones = _github_json(
        f"https://api.github.com/repos/{owner}/{name}/milestones?state=all&per_page=100",
        token,
    )
    match = next((item for item in milestones if item.get("title") == milestone), None)
    if match is None:
        return _result("milestone", False, "", f"milestone {milestone!r} does not exist")

    open_issues = int(match.get("open_issues", 0))
    state = match.get("state")
    ok = state == "closed" and open_issues == 0
    return _result(
        "milestone",
        ok,
        f"milestone {milestone!r} is closed with no open issues",
        f"milestone {milestone!r} has state={state!r} and open_issues={open_issues}",
    )


def _check_blocker_query(repository: str, query: str, token: str) -> dict[str, object]:
    search = f"repo:{repository} is:open {query}".strip()
    payload = _github_json(
        "https://api.github.com/search/issues?q=" + quote(search),
        token,
    )
    count = int(payload.get("total_count", 0))
    return _result(
        f"blocker:{query}",
        count == 0,
        f"no open items match {query!r}",
        f"{count} open item(s) match {query!r}",
    )


def _github_json(url: str, token: str) -> object:
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "LibreCodeCoop/github-workflows",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def _result(name: str, ok: bool, success: str, failure: str) -> dict[str, object]:
    return {"name": name, "ok": ok, "message": success if ok else failure}


def _split_repository(repository: str) -> tuple[str, str]:
    parts = repository.split("/", 1)
    if len(parts) != 2 or not all(parts):
        raise ValueError("repository must use OWNER/REPO format")
    return parts[0], parts[1]


def _required(value: str | None, name: str) -> str:
    if not value:
        raise ValueError(f"{name} is required for GitHub checks")
    return value


def parse_blocker_queries(value: str) -> tuple[str, ...]:
    try:
        queries = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError(f"blocker queries must be valid JSON: {error.msg}") from error

    if not isinstance(queries, list) or not all(isinstance(item, str) for item in queries):
        raise ValueError("blocker queries must be a JSON array of strings")

    return tuple(queries)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--stable-branch", required=True)
    parser.add_argument("--current-ref", required=True)
    parser.add_argument("--repository")
    parser.add_argument("--appinfo", type=Path, default=Path("appinfo/info.xml"))
    parser.add_argument("--changelog", type=Path, default=Path("CHANGELOG.md"))
    parser.add_argument("--milestone", default="")
    parser.add_argument("--blocker-queries-json", default="[]")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        plan = build_plan(
            PlanInput(
                version=args.version,
                stable_branch=args.stable_branch,
                current_ref=args.current_ref,
                repository=args.repository,
                appinfo=args.appinfo,
                changelog=args.changelog,
                milestone=args.milestone or None,
                blocker_queries=parse_blocker_queries(args.blocker_queries_json),
            ),
            token=os.environ.get("GITHUB_TOKEN"),
        )
    except (ValueError, OSError) as error:
        print(f"release-plan: {error}", file=sys.stderr)
        return 2

    rendered = json.dumps(plan, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")

    return 0 if plan["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
