#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

ApiRequest = Callable[[str], Any]


class ActionError(RuntimeError):
    pass


def sanitize_markdown_text(value: str) -> str:
    normalized = " ".join(value.replace("\r", "\n").splitlines()).strip()
    for character in ("\\", "`", "*", "_", "{", "}", "[", "]", "<", ">"):
        normalized = normalized.replace(character, f"\\{character}")
    # PR titles and commit subjects can be contributor-controlled. Keep their
    # visible text while preventing them from creating GitHub @mentions.
    return normalized.replace("@", "@\u200b")


def choose_pull_request(
    pull_requests: list[dict[str, Any]],
    preferred_branch: str,
) -> dict[str, Any] | None:
    merged = [
        pr
        for pr in pull_requests
        if pr.get("merged_at") and isinstance(pr.get("number"), int)
    ]
    if not merged:
        return None

    preferred = [
        pr
        for pr in merged
        if isinstance(pr.get("base"), dict)
        and pr["base"].get("ref") == preferred_branch
    ]
    candidates = preferred or merged
    return min(candidates, key=lambda pr: int(pr["number"]))


def build_api_request(url: str, token: str) -> urllib.request.Request:
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    request.add_unredirected_header("Authorization", f"Bearer {token}")
    return request


def github_api_get(url: str, token: str) -> Any:
    request = build_api_request(url, token)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise ActionError(
            f"GitHub API request failed ({error.code}): {body}"
        ) from error
    return json.loads(body)


def git_lines(working_directory: Path, *args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=working_directory,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def enumerate_commits(
    working_directory: Path,
    from_ref: str,
    to_ref: str,
    fallback_limit: int,
) -> list[str]:
    if from_ref:
        return git_lines(
            working_directory,
            "rev-list",
            "--reverse",
            f"{from_ref}..{to_ref}",
        )
    return git_lines(
        working_directory,
        "rev-list",
        "--reverse",
        f"--max-count={fallback_limit}",
        to_ref,
    )


def commit_subject(working_directory: Path, sha: str) -> str:
    lines = git_lines(working_directory, "show", "-s", "--format=%s", sha)
    if not lines:
        raise ActionError(f"cannot resolve subject for commit {sha}")
    return sanitize_markdown_text(lines[0])


def generate_changes(
    *,
    commits: list[str],
    repository: str,
    branch: str,
    server_url: str,
    api_url: str,
    token: str,
    subject_lookup: Callable[[str], str],
    request: Callable[[str, str], Any] = github_api_get,
) -> tuple[list[str], int, int]:
    seen_pull_requests: set[int] = set()
    lines: list[str] = []
    pull_request_count = 0
    commit_fallback_count = 0

    owner, repo = repository.split("/", 1)
    clean_server_url = server_url.rstrip("/")
    clean_api_url = api_url.rstrip("/")

    for sha in commits:
        pull_requests = request(
            f"{clean_api_url}/repos/{owner}/{repo}/commits/{sha}/pulls",
            token,
        )
        if not isinstance(pull_requests, list):
            raise ActionError(
                f"unexpected pull request response for commit {sha}"
            )

        pull_request = choose_pull_request(pull_requests, branch)
        if pull_request is not None:
            number = int(pull_request["number"])
            if number in seen_pull_requests:
                continue
            seen_pull_requests.add(number)
            title = sanitize_markdown_text(str(pull_request.get("title") or ""))
            if not title:
                title = f"Pull request #{number}"
            url = f"{clean_server_url}/{repository}/pull/{number}"
            lines.append(f"- {title} ([#{number}]({url}))")
            pull_request_count += 1
            continue

        subject = subject_lookup(sha)
        lines.append(f"- {subject} (`{sha[:7]}`)")
        commit_fallback_count += 1

    return lines, pull_request_count, commit_fallback_count


def write_output(name: str, value: str) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if not output:
        return
    with Path(output).open("a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def main() -> int:
    token = os.environ.get("RELEASE_NOTES_GITHUB_TOKEN", "")
    repository = os.environ.get("RELEASE_NOTES_REPOSITORY", "")
    branch = os.environ.get("RELEASE_NOTES_BRANCH", "")
    working_directory = Path(
        os.environ.get("RELEASE_NOTES_WORKING_DIRECTORY", ".")
    ).resolve()
    from_ref = os.environ.get("RELEASE_NOTES_FROM_REF", "").strip()
    to_ref = os.environ.get("RELEASE_NOTES_TO_REF", "HEAD").strip() or "HEAD"
    fallback_limit_raw = os.environ.get("RELEASE_NOTES_FALLBACK_LIMIT", "10")
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com")

    if not token:
        raise ActionError("github token is required")
    if repository.count("/") != 1:
        raise ActionError("repository must be in owner/name form")
    if not branch:
        raise ActionError("branch is required")
    if not working_directory.is_dir():
        raise ActionError(f"working directory does not exist: {working_directory}")

    try:
        fallback_limit = int(fallback_limit_raw)
    except ValueError as error:
        raise ActionError("fallback-limit must be an integer") from error
    if fallback_limit <= 0:
        raise ActionError("fallback-limit must be greater than zero")

    commits = enumerate_commits(
        working_directory,
        from_ref,
        to_ref,
        fallback_limit,
    )
    lines, pull_request_count, commit_fallback_count = generate_changes(
        commits=commits,
        repository=repository,
        branch=branch,
        server_url=server_url,
        api_url=api_url,
        token=token,
        subject_lookup=lambda sha: commit_subject(working_directory, sha),
    )

    runner_temp = Path(os.environ.get("RUNNER_TEMP", tempfile.gettempdir()))
    runner_temp.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix="release-note-changes-",
        suffix=".md",
        dir=runner_temp,
        delete=False,
    ) as handle:
        for line in lines:
            handle.write(f"{line}\n")
        changes_file = Path(handle.name)

    write_output("changes-file", str(changes_file))
    write_output("change-count", str(len(lines)))
    write_output("pull-request-count", str(pull_request_count))
    write_output("commit-fallback-count", str(commit_fallback_count))

    print(
        f"Generated {len(lines)} change entries "
        f"({pull_request_count} pull requests, "
        f"{commit_fallback_count} direct commits)."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        ActionError,
        OSError,
        subprocess.CalledProcessError,
        json.JSONDecodeError,
    ) as error:
        print(f"::error::{error}")
        raise SystemExit(1) from error
