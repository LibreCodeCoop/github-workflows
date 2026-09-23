#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

MARKER = "<!-- librecode:first-merged-pr-comment -->"
PLACEHOLDER = re.compile(r"\{([a-z][a-z0-9_]*)(?:\|([a-z][a-z0-9_]*))?\}")
ALLOWED_FILTERS = {"urlencode"}


class ActionError(RuntimeError):
    pass


def render_template(template: str, context: dict[str, str]) -> str:
    if not template.strip():
        raise ActionError("message template is empty")

    def replace(match: re.Match[str]) -> str:
        name, filter_name = match.groups()
        if name not in context:
            raise ActionError(f"unknown placeholder: {name}")
        value = context[name]
        if filter_name is None:
            return value
        if filter_name not in ALLOWED_FILTERS:
            raise ActionError(f"unknown placeholder filter: {filter_name}")
        if filter_name == "urlencode":
            return urllib.parse.quote(value, safe="")
        raise AssertionError(filter_name)

    return PLACEHOLDER.sub(replace, template)


def build_context(
    *,
    pr: dict[str, Any],
    repository: str,
    server_url: str,
    api_url: str,
) -> dict[str, str]:
    owner, repository_name = repository.split("/", 1)
    login = str(pr["user"]["login"])
    number = str(pr["number"])
    return {
        "server_url": server_url.rstrip("/"),
        "api_url": api_url.rstrip("/"),
        "repository": repository,
        "repository_owner": owner,
        "repository_name": repository_name,
        "repository_url": f"{server_url.rstrip('/')}/{repository}",
        "pull_request_number": number,
        "pull_request_url": str(
            pr.get("html_url")
            or f"{server_url.rstrip('/')}/{repository}/pull/{number}"
        ),
        "contributor_login": login,
        "contributor_mention": f"@{login}",
        "contributor_url": f"{server_url.rstrip('/')}/{login}",
        "merge_commit_sha": str(pr.get("merge_commit_sha") or ""),
    }


def api_request(
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise ActionError(f"GitHub API request failed ({error.code}): {body}") from error
    return json.loads(body) if body else None


def pull_request_from_event(event_path: str) -> dict[str, Any] | None:
    if not event_path:
        return None
    payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
    pr = payload.get("pull_request")
    return pr if isinstance(pr, dict) else None


def write_output(name: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with Path(path).open("a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def first_merged_query(repository: str, login: str, closed_at: str) -> str:
    return " ".join(
        (
            f"repo:{repository}",
            "is:pr",
            "is:merged",
            f"author:{login}",
            f"closed:<={closed_at}",
        )
    )


def main() -> int:
    token = os.environ.get("FIRST_MERGED_PR_GITHUB_TOKEN", "")
    template = os.environ.get("FIRST_MERGED_PR_MESSAGE_TEMPLATE", "")
    manual_number = os.environ.get("FIRST_MERGED_PR_NUMBER", "").strip()
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")

    if not token:
        raise ActionError("github token is required")
    if "/" not in repository:
        raise ActionError("GITHUB_REPOSITORY must be in owner/name form")

    pr = pull_request_from_event(os.environ.get("GITHUB_EVENT_PATH", ""))
    if pr is None:
        if not manual_number.isdigit() or int(manual_number) <= 0:
            raise ActionError("a valid pull-request-number is required for a manual run")
        owner, repo = repository.split("/", 1)
        pr = api_request(
            "GET",
            f"{api_url}/repos/{owner}/{repo}/pulls/{int(manual_number)}",
            token,
        )

    write_output("contributor-login", str(pr["user"]["login"]))
    write_output("pull-request-number", str(pr["number"]))

    if not pr.get("merged") or pr.get("user", {}).get("type") == "Bot":
        write_output("is-first-merged", "false")
        write_output("comment-created", "false")
        print("Pull request is not a merged human contribution; skipping.")
        return 0

    login = str(pr["user"]["login"])
    closed_at = str(pr["closed_at"])
    query = first_merged_query(repository, login, closed_at)
    encoded_query = urllib.parse.urlencode({"q": query, "per_page": 2})
    search = api_request("GET", f"{api_url}/search/issues?{encoded_query}", token)
    total_count = int(search["total_count"])

    if total_count != 1:
        write_output("is-first-merged", "false")
        write_output("comment-created", "false")
        print(
            f"PR #{pr['number']} is not the contributor's first merged pull request; "
            f"found {total_count} merged pull requests up to this one."
        )
        return 0

    write_output("is-first-merged", "true")

    owner, repo = repository.split("/", 1)
    comments = api_request(
        "GET",
        f"{api_url}/repos/{owner}/{repo}/issues/{pr['number']}/comments?per_page=100",
        token,
    )
    if any(MARKER in str(comment.get("body") or "") for comment in comments):
        write_output("comment-created", "false")
        print(f"PR #{pr['number']} already has a first-merged comment; skipping.")
        return 0

    context = build_context(
        pr=pr,
        repository=repository,
        server_url=server_url,
        api_url=api_url,
    )
    message = render_template(template, context).strip()
    api_request(
        "POST",
        f"{api_url}/repos/{owner}/{repo}/issues/{pr['number']}/comments",
        token,
        {"body": f"{MARKER}\n{message}"},
    )
    write_output("comment-created", "true")
    print(f"Created first-merged contribution comment on PR #{pr['number']}.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ActionError, KeyError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"::error::{error}")
        raise SystemExit(1) from error
