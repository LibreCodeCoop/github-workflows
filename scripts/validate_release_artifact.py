#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import argparse
import tarfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree


def validate_artifact(artifact: Path, app_name: str, version: str) -> None:
    if not artifact.is_file():
        raise ValueError(f"artifact does not exist: {artifact}")

    with tarfile.open(artifact, "r:gz") as archive:
        members = archive.getmembers()
        if not members:
            raise ValueError("artifact is empty")

        top_levels: set[str] = set()
        for member in members:
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"unsafe archive path: {member.name}")
            if path.parts:
                top_levels.add(path.parts[0])

        if top_levels != {app_name}:
            raise ValueError(
                f"artifact must contain only the top-level directory {app_name!r}; "
                f"found {sorted(top_levels)!r}"
            )

        info_path = f"{app_name}/appinfo/info.xml"
        try:
            info_member = archive.getmember(info_path)
        except KeyError as error:
            raise ValueError(f"artifact is missing {info_path}") from error

        stream = archive.extractfile(info_member)
        if stream is None:
            raise ValueError(f"artifact entry is not a file: {info_path}")

        try:
            root = ElementTree.parse(stream).getroot()
        except ElementTree.ParseError as error:
            raise ValueError(f"cannot parse {info_path}: {error}") from error

        declared = root.findtext("version")
        if declared != version:
            raise ValueError(
                f"{info_path} declares version {declared!r}, expected {version!r}"
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--app-name", required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()

    try:
        validate_artifact(args.artifact, args.app_name, args.version)
    except (OSError, ValueError, tarfile.TarError) as error:
        parser.error(str(error))

    print(f"Validated release artifact: {args.artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
