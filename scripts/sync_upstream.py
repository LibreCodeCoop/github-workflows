#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    sha256: str
    destination: Path


def load_sources(manifest_path: Path) -> list[Source]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest must be a JSON object")

    raw_sources = payload.get("sources")
    if not isinstance(raw_sources, list):
        raise ValueError("manifest.sources must be an array")

    sources: list[Source] = []
    for index, raw in enumerate(raw_sources):
        if not isinstance(raw, dict):
            raise ValueError(f"manifest.sources[{index}] must be an object")

        name = _non_empty_string(raw.get("name"), f"sources[{index}].name")
        url = _non_empty_string(raw.get("url"), f"sources[{index}].url")
        digest = _non_empty_string(raw.get("sha256"), f"sources[{index}].sha256")
        destination = _non_empty_string(
            raw.get("destination"), f"sources[{index}].destination"
        )

        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError(f"sources[{index}].sha256 must be 64 lowercase hex characters")
        if "/refs/heads/" in url or url.endswith(("/main", "/master")):
            raise ValueError(f"sources[{index}].url must be pinned to an immutable commit")

        sources.append(
            Source(
                name=name,
                url=url,
                sha256=digest,
                destination=Path(destination),
            )
        )

    return sources


def fetch(source: Source) -> bytes:
    request = Request(source.url, headers={"User-Agent": "github-workflows-sync"})
    with urlopen(request, timeout=30) as response:
        content = response.read()

    actual = hashlib.sha256(content).hexdigest()
    if actual != source.sha256:
        raise ValueError(
            f"{source.name}: SHA-256 mismatch: expected {source.sha256}, got {actual}"
        )
    return content


def sync(sources: list[Source], root: Path) -> None:
    for source in sources:
        content = fetch(source)
        destination = _safe_destination(root, source.destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)


def check(sources: list[Source], root: Path) -> None:
    drift: list[str] = []
    for source in sources:
        expected = fetch(source)
        destination = _safe_destination(root, source.destination)
        if not destination.exists() or destination.read_bytes() != expected:
            drift.append(source.name)

    if drift:
        raise ValueError("generated templates are out of date: " + ", ".join(drift))


def _safe_destination(root: Path, destination: Path) -> Path:
    if destination.is_absolute() or ".." in destination.parts:
        raise ValueError(f"unsafe destination: {destination}")
    resolved = (root / destination).resolve()
    root_resolved = root.resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise ValueError(f"destination escapes repository root: {destination}")
    return resolved


def _non_empty_string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path} must be a non-empty string")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("sync", "check"))
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()

    root = Path.cwd()
    sources = load_sources(args.manifest)

    try:
        if args.command == "sync":
            sync(sources, root)
        else:
            check(sources, root)
    except ValueError as error:
        parser.error(str(error))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
