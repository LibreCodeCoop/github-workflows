#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

VERSION_RE = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?:-(?P<pre>[A-Za-z0-9.-]+))?$")
HEADING_RE = re.compile(r"^(#{2,3})\s+(.+?)\s*$")
LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
CODE_RE = re.compile(r"`([^`]+)`")
RST_HEADER = [
    ".. SPDX-FileCopyrightText: 2026 LibreCode coop and contributors",
    ".. SPDX-License-" + "Identifier: AGPL-3.0-or-later",
    "",
]


def load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def inline_rst(text: str) -> str:
    text = CODE_RE.sub(lambda match: f"``{match.group(1)}``", text)
    text = LINK_RE.sub(lambda match: f"`{match.group(1)} <{match.group(2)}>`_", text)
    return text


def markdown_section_to_rst(section: str, version: str) -> str:
    lines = section.strip().splitlines()
    if not lines:
        raise ValueError("changelog section must not be empty")

    output: list[str] = [*RST_HEADER, ".. This file is generated from LibreSign/libresign release history.", ""]
    first_heading_seen = False
    for raw in lines:
        match = HEADING_RE.match(raw)
        if match:
            level, title = match.groups()
            title = inline_rst(title)
            if level == "##":
                if first_heading_seen:
                    raise ValueError("release section contains more than one version heading")
                first_heading_seen = True
                if not title.startswith(version):
                    raise ValueError(f"release heading does not start with version {version}")
                output.extend([title, "=" * len(title), ""])
            else:
                output.extend([title, "-" * len(title), ""])
            continue

        if raw.startswith("- "):
            output.append("* " + inline_rst(raw[2:]))
        else:
            output.append(inline_rst(raw))

    if not first_heading_seen:
        raise ValueError("release section does not contain a version heading")
    return "\n".join(output).rstrip() + "\n"


def release_filename(version: str) -> str:
    if VERSION_RE.fullmatch(version) is None:
        raise ValueError(f"unsupported release version: {version}")
    return f"{version}.rst"


def version_key(version: str) -> tuple[int, int, int, int, int, str]:
    match = VERSION_RE.fullmatch(version)
    if match is None:
        raise ValueError(f"unsupported release version: {version}")

    prerelease = match.group("pre")
    if prerelease is None:
        stage_rank = 4
        sequence = 0
        fallback = ""
    else:
        parts = prerelease.split(".", 1)
        stage_rank = {"alpha": 1, "beta": 2, "rc": 3}.get(parts[0].lower(), 0)
        sequence = int(parts[1]) if len(parts) == 2 and parts[1].isdigit() else 0
        fallback = prerelease

    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        stage_rank,
        sequence,
        fallback,
    )


def render_major_index(major: int, versions: list[str]) -> str:
    ordered = sorted(versions, key=version_key, reverse=True)
    title = f"LibreSign {major}"
    body = [
        *RST_HEADER,
        ".. This file is generated from LibreSign release history. Do not edit release text here manually.",
        "",
        title,
        "=" * len(title),
        "",
        ".. toctree::",
        "   :maxdepth: 1",
        "",
    ]
    body.extend(f"   {version}" for version in ordered)
    return "\n".join(body) + "\n"


def render_root_index(majors: list[int]) -> str:
    title = "Release history"
    body = [
        *RST_HEADER,
        ".. This file is generated. Release text is sourced from LibreSign/libresign per-major changelogs.",
        "",
        title,
        "=" * len(title),
        "",
        "Published LibreSign release history is generated after publication verification succeeds.",
        "",
        ".. toctree::",
        "   :maxdepth: 2",
        "",
    ]
    body.extend(f"   LibreSign {major} <{major}/index>" for major in sorted(majors, reverse=True))
    return "\n".join(body) + "\n"


def synchronize(prepared_path: Path, verification_path: Path, docs_root: Path) -> tuple[Path, Path, Path]:
    prepared = load_json(prepared_path)
    verification = load_json(verification_path)

    if verification.get("success") is not True:
        raise ValueError("PublicationVerification is not successful")
    if verification.get("prepared_release_id") != prepared.get("id"):
        raise ValueError("PublicationVerification does not reference the supplied PreparedRelease")
    github_release = verification.get("github_release")
    if not isinstance(github_release, dict) or github_release.get("published") is not True:
        raise ValueError("GitHub Release is not confirmed as published")

    version = prepared.get("version")
    changelog = prepared.get("changelog")
    if not isinstance(version, str) or VERSION_RE.fullmatch(version) is None:
        raise ValueError("PreparedRelease contains an invalid version")
    if not isinstance(changelog, dict) or not isinstance(changelog.get("section"), str):
        raise ValueError("PreparedRelease does not contain a changelog section")

    major = int(version.split(".", 1)[0])
    history_root = docs_root / "developer_manual" / "release-history"
    major_root = history_root / str(major)
    major_root.mkdir(parents=True, exist_ok=True)

    release_path = major_root / release_filename(version)
    release_path.write_text(markdown_section_to_rst(changelog["section"], version), encoding="utf-8")

    versions = [path.stem for path in major_root.glob("*.rst") if path.name != "index.rst"]
    major_index = major_root / "index.rst"
    major_index.write_text(render_major_index(major, versions), encoding="utf-8")

    majors = [int(path.name) for path in history_root.iterdir() if path.is_dir() and path.name.isdigit()]
    root_index = history_root / "index.rst"
    root_index.write_text(render_root_index(majors), encoding="utf-8")

    return release_path, major_index, root_index


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared", required=True, type=Path)
    parser.add_argument("--verification", required=True, type=Path)
    parser.add_argument("--docs-root", required=True, type=Path)
    args = parser.parse_args()
    release_path, major_index, root_index = synchronize(args.prepared, args.verification, args.docs_root)
    print(json.dumps({
        "release_path": str(release_path),
        "major_index": str(major_index),
        "root_index": str(root_index),
    }, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
