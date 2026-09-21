#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
STABLE_REF_RE = re.compile(r"^refs/heads/(stable([1-9][0-9]*))$")
STABLE_BRANCH_RE = re.compile(r"^stable([1-9][0-9]*)$")


@dataclass(frozen=True)
class StableState:
    current_branch: str
    current_major: int | None
    latest_branch: str | None
    latest_major: int | None

    @property
    def is_latest(self) -> bool:
        return self.latest_branch is not None and self.current_branch == self.latest_branch


def parse_stable_refs(output: str) -> dict[int, str]:
    branches: dict[int, str] = {}
    for raw_line in output.splitlines():
        parts = raw_line.strip().split()
        if len(parts) != 2:
            continue
        match = STABLE_REF_RE.fullmatch(parts[1])
        if match is None:
            continue
        branch = match.group(1)
        major = int(match.group(2))
        branches[major] = branch
    return branches


def resolve_state(current_branch: str, branches: dict[int, str]) -> StableState:
    current_match = STABLE_BRANCH_RE.fullmatch(current_branch)
    current_major = int(current_match.group(1)) if current_match else None

    if not branches:
        return StableState(current_branch, current_major, None, None)

    latest_major = max(branches)
    return StableState(
        current_branch=current_branch,
        current_major=current_major,
        latest_branch=branches[latest_major],
        latest_major=latest_major,
    )


def list_remote_stable_refs(repository: str) -> str:
    if REPOSITORY_RE.fullmatch(repository) is None:
        raise ValueError(f"invalid repository: {repository!r}")

    result = subprocess.run(
        [
            "git",
            "ls-remote",
            "--heads",
            f"https://github.com/{repository}.git",
            "refs/heads/stable*",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout


def write_output(name: str, value: str) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")


def write_summary(state: StableState) -> None:
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary:
        return

    current_major = str(state.current_major) if state.current_major is not None else "n/a"
    latest_branch = state.latest_branch or "none"
    latest_major = str(state.latest_major) if state.latest_major is not None else "n/a"
    with Path(summary).open("a", encoding="utf-8") as handle:
        handle.write(
            "### Stable release branch selection\n\n"
            f"- Current branch: `{state.current_branch}`\n"
            f"- Current release line: `{current_major}`\n"
            f"- Latest stable branch: `{latest_branch}`\n"
            f"- Latest release line: `{latest_major}`\n"
            f"- Publish nightly: `{str(state.is_latest).lower()}`\n"
        )


def main() -> int:
    repository = os.environ.get("INPUT_REPOSITORY") or os.environ.get("GITHUB_REPOSITORY", "")
    branch = os.environ.get("INPUT_BRANCH") or os.environ.get("GITHUB_REF_NAME", "")

    refs = parse_stable_refs(list_remote_stable_refs(repository))
    state = resolve_state(branch, refs)

    print(f"Current branch: {state.current_branch}")
    print(f"Current release line: {state.current_major if state.current_major is not None else 'n/a'}")
    print(f"Latest stable branch: {state.latest_branch or 'none'}")
    print(f"Latest release line: {state.latest_major if state.latest_major is not None else 'n/a'}")
    print(f"Publish nightly: {str(state.is_latest).lower()}")

    write_output("current_branch", state.current_branch)
    write_output("current_major", "" if state.current_major is None else str(state.current_major))
    write_output("latest_branch", state.latest_branch or "")
    write_output("latest_major", "" if state.latest_major is None else str(state.latest_major))
    write_output("is_latest", str(state.is_latest).lower())
    write_summary(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
