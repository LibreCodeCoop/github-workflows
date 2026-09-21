#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

SEMVER = re.compile(r"^(?P<major>[0-9]+)\.(?P<minor>[0-9]+)\.(?P<patch>[0-9]+)$")
STABLE = re.compile(r"^stable(?P<major>[0-9]+)$")


@dataclass(frozen=True)
class ReleaseLine:
    branch: str
    head_sha: str
    current_version: str
    nextcloud_major: int
    previous_tag: str | None
    proposed_version: str
    requested_version: str
    milestone: str
    ready: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]


def _git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise ValueError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def _read_at(repo: Path, ref: str, path: str) -> str:
    return _git(repo, "show", f"{ref}:{path}")


def _parse_appinfo(content: str) -> tuple[str, int]:
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as error:
        raise ValueError(f"invalid appinfo XML: {error}") from error

    version = (root.findtext("version") or "").strip()
    if not SEMVER.fullmatch(version):
        raise ValueError(f"appinfo version must use MAJOR.MINOR.PATCH, got {version!r}")

    nextcloud = root.find("./dependencies/nextcloud")
    if nextcloud is None:
        raise ValueError("appinfo is missing dependencies/nextcloud")

    min_version = nextcloud.attrib.get("min-version", "")
    max_version = nextcloud.attrib.get("max-version", "")
    if not min_version.isdigit():
        raise ValueError("nextcloud min-version must be an integer")
    if max_version and max_version != min_version:
        raise ValueError(
            f"LibreSign-style release line requires matching min/max Nextcloud major, got {min_version}/{max_version}"
        )

    return version, int(min_version)


def _previous_release_tag(repo: Path, branch: str) -> str | None:
    output = _git(
        repo,
        "describe",
        "--tags",
        "--match",
        "v[0-9]*.[0-9]*.[0-9]*",
        "--abbrev=0",
        branch,
        check=False,
    )
    return output or None


def _version_from_tag(tag: str | None, fallback: str) -> str:
    value = tag[1:] if tag and tag.startswith("v") else fallback
    if not SEMVER.fullmatch(value):
        raise ValueError(f"cannot derive semantic version from {value!r}")
    return value


def _next_patch(version: str) -> str:
    match = SEMVER.fullmatch(version)
    if match is None:
        raise ValueError(f"invalid semantic version: {version}")
    return f"{match.group('major')}.{match.group('minor')}.{int(match.group('patch')) + 1}"


def _parse_json_mapping(value: str, name: str) -> dict[str, str]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError(f"{name} must be valid JSON: {error.msg}") from error
    if not isinstance(parsed, dict) or not all(
        isinstance(key, str) and isinstance(item, str)
        for key, item in parsed.items()
    ):
        raise ValueError(f"{name} must be a JSON object of string keys and values")
    return parsed


def _parse_branches(value: str) -> tuple[str, ...]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError(f"branches must be valid JSON: {error.msg}") from error
    if not isinstance(parsed, list) or not parsed or not all(
        isinstance(item, str) and item for item in parsed
    ):
        raise ValueError("branches must be a non-empty JSON array of strings")
    if len(set(parsed)) != len(parsed):
        raise ValueError("branches must not contain duplicates")
    return tuple(parsed)


def _branch_sort_key(branch: str) -> tuple[int, str]:
    match = STABLE.fullmatch(branch)
    if match:
        return (int(match.group("major")), branch)
    return (10**9, branch)


def build_release_train(
    repo: Path,
    branches: tuple[str, ...],
    version_overrides: dict[str, str],
) -> dict[str, object]:
    lines: list[ReleaseLine] = []

    for branch in sorted(branches, key=_branch_sort_key):
        blockers: list[str] = []
        warnings: list[str] = []

        head_sha = _git(repo, "rev-parse", "--verify", f"{branch}^{{commit}}", check=False)
        if not head_sha:
            lines.append(
                ReleaseLine(
                    branch=branch,
                    head_sha="",
                    current_version="",
                    nextcloud_major=-1,
                    previous_tag=None,
                    proposed_version="",
                    requested_version=version_overrides.get(branch, ""),
                    milestone="",
                    ready=False,
                    blockers=(f"branch {branch!r} does not exist",),
                    warnings=(),
                )
            )
            continue

        try:
            current_version, nextcloud_major = _parse_appinfo(
                _read_at(repo, branch, "appinfo/info.xml")
            )
        except ValueError as error:
            lines.append(
                ReleaseLine(
                    branch=branch,
                    head_sha=head_sha,
                    current_version="",
                    nextcloud_major=-1,
                    previous_tag=None,
                    proposed_version="",
                    requested_version=version_overrides.get(branch, ""),
                    milestone="",
                    ready=False,
                    blockers=(str(error),),
                    warnings=(),
                )
            )
            continue

        branch_match = STABLE.fullmatch(branch)
        if branch_match and int(branch_match.group("major")) != nextcloud_major:
            blockers.append(
                f"{branch} implies Nextcloud {branch_match.group('major')} but appinfo declares {nextcloud_major}"
            )

        previous_tag = _previous_release_tag(repo, branch)
        previous_version = _version_from_tag(previous_tag, current_version)
        proposed_version = _next_patch(previous_version)
        requested_version = version_overrides.get(branch, proposed_version)

        if not SEMVER.fullmatch(requested_version):
            blockers.append(
                f"requested version {requested_version!r} must use MAJOR.MINOR.PATCH"
            )

        expected_major = int(SEMVER.fullmatch(current_version).group("major"))
        requested_match = SEMVER.fullmatch(requested_version)
        if requested_match and int(requested_match.group("major")) != expected_major:
            warnings.append(
                "requested version changes the app major; review explicitly before preparation"
            )

        if _git(repo, "rev-parse", "-q", "--verify", f"refs/tags/v{requested_version}", check=False):
            blockers.append(f"tag v{requested_version} already exists")

        if requested_version != proposed_version:
            warnings.append(
                f"version override selected: proposed {proposed_version}, requested {requested_version}"
            )

        milestone = (
            f"Next Patch ({nextcloud_major})"
            if branch_match
            else f"Next Major ({nextcloud_major})"
        )

        lines.append(
            ReleaseLine(
                branch=branch,
                head_sha=head_sha,
                current_version=current_version,
                nextcloud_major=nextcloud_major,
                previous_tag=previous_tag,
                proposed_version=proposed_version,
                requested_version=requested_version,
                milestone=milestone,
                ready=not blockers,
                blockers=tuple(blockers),
                warnings=tuple(warnings),
            )
        )

    return {
        "ready": all(line.ready for line in lines),
        "publication_order": [line.branch for line in lines],
        "releases": [
            {
                "branch": line.branch,
                "head_sha": line.head_sha,
                "current_version": line.current_version,
                "nextcloud_major": line.nextcloud_major,
                "previous_tag": line.previous_tag,
                "proposed_version": line.proposed_version,
                "requested_version": line.requested_version,
                "milestone": line.milestone,
                "ready": line.ready,
                "blockers": list(line.blockers),
                "warnings": list(line.warnings),
            }
            for line in lines
        ],
    }


def render_summary(plan: dict[str, object]) -> str:
    lines = [
        "## Release train plan",
        "",
        f"Overall readiness: **{'ready' if plan['ready'] else 'blocked'}**",
        "",
        "| Branch | Current | Previous tag | Proposed | Requested | Milestone | Status |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for release in plan["releases"]:
        status = "ready" if release["ready"] else "blocked"
        lines.append(
            "| {branch} | {current_version} | {previous_tag} | {proposed_version} | "
            "{requested_version} | {milestone} | {status} |".format(
                previous_tag=release["previous_tag"] or "-",
                status=status,
                **release,
            )
        )
        for blocker in release["blockers"]:
            lines.append(f"- **{release['branch']} blocker:** {blocker}")
        for warning in release["warnings"]:
            lines.append(f"- **{release['branch']} warning:** {warning}")
    lines.append("")
    return "\n".join(lines)


def _write_output(name: str, value: str) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if not output:
        return
    with Path(output).open("a", encoding="utf-8") as stream:
        delimiter = f"RELEASE_TRAIN_{name.upper()}"
        stream.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument(
        "--branches-json",
        default=os.environ.get("RELEASE_TRAIN_BRANCHES", "[]"),
    )
    parser.add_argument(
        "--version-overrides-json",
        default=os.environ.get("RELEASE_TRAIN_VERSION_OVERRIDES", "{}"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(os.environ.get("RELEASE_TRAIN_OUTPUT", "release-train-plan.json")),
    )
    args = parser.parse_args()

    try:
        branches = _parse_branches(args.branches_json)
        overrides = _parse_json_mapping(
            args.version_overrides_json, "version overrides"
        )
        unknown = sorted(set(overrides) - set(branches))
        if unknown:
            raise ValueError(
                "version overrides reference branches not in the train: "
                + ", ".join(unknown)
            )
        plan = build_release_train(args.repo.resolve(), branches, overrides)
    except (OSError, ValueError) as error:
        print(f"release-train-plan: {error}", file=sys.stderr)
        return 2

    rendered = json.dumps(plan, indent=2, sort_keys=True)
    args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)

    summary = render_summary(plan)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as stream:
            stream.write(summary)

    _write_output("plan", json.dumps(plan, separators=(",", ":")))
    _write_output("ready", str(plan["ready"]).lower())
    _write_output(
        "publication_order",
        json.dumps(plan["publication_order"], separators=(",", ":")),
    )
    return 0 if plan["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
