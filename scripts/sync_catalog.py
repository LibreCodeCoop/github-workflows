#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

PUBLISHABLE_SUFFIXES = (".yml", ".yaml", ".properties.json", ".svg")


def is_publishable(path: Path) -> bool:
    return path.is_file() and path.name.endswith(PUBLISHABLE_SUFFIXES)


def load_catalog_manifest(path: Path) -> tuple[str, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("catalog manifest must be a JSON object")

    templates = payload.get("templates")
    if (
        not isinstance(templates, list)
        or not templates
        or not all(isinstance(item, str) and item for item in templates)
    ):
        raise ValueError("catalog manifest must contain a non-empty templates array")

    if len(set(templates)) != len(templates):
        raise ValueError("catalog manifest contains duplicate template names")

    for template in templates:
        if Path(template).name != template:
            raise ValueError(f"invalid catalog template name: {template}")

    return tuple(sorted(templates))


def collect_publishable(
    directory: Path,
    template_names: tuple[str, ...] | None = None,
) -> dict[str, Path]:
    if not directory.is_dir():
        raise ValueError(f"directory does not exist: {directory}")

    all_files = {
        path.name: path
        for path in directory.iterdir()
        if is_publishable(path)
    }

    if template_names is None:
        files = all_files
    else:
        files: dict[str, Path] = {}

        for template in template_names:
            yml_name = f"{template}.yml"
            yaml_name = f"{template}.yaml"
            candidates = [
                name
                for name in (yml_name, yaml_name)
                if name in all_files
            ]
            if len(candidates) != 1:
                raise ValueError(
                    f"catalog template must have exactly one workflow file: {template}"
                )

            metadata_name = f"{template}.properties.json"
            if metadata_name not in all_files:
                raise ValueError(f"missing template metadata: {metadata_name}")

            files[candidates[0]] = all_files[candidates[0]]
            files[metadata_name] = all_files[metadata_name]

        for template in template_names:
            metadata_name = f"{template}.properties.json"
            metadata = json.loads(
                files[metadata_name].read_text(encoding="utf-8")
            )
            icon_name = metadata.get("iconName") if isinstance(metadata, dict) else None
            if (
                isinstance(icon_name, str)
                and icon_name
                and not icon_name.startswith("octicon ")
            ):
                icon_file = f"{icon_name}.svg"
                if icon_file not in all_files:
                    raise ValueError(
                        f"metadata references missing icon {icon_file}: {metadata_name}"
                    )
                files[icon_file] = all_files[icon_file]

    validate_catalog(files)
    return files


def validate_catalog(files: dict[str, Path]) -> None:
    workflow_names: set[str] = set()

    for name in files:
        if name.endswith(".yml"):
            workflow_names.add(name[:-4])
        elif name.endswith(".yaml"):
            workflow_names.add(name[:-5])

    for workflow_name in workflow_names:
        metadata_name = f"{workflow_name}.properties.json"
        if metadata_name not in files:
            raise ValueError(f"missing template metadata: {metadata_name}")

    for name, path in files.items():
        if not name.endswith(".properties.json"):
            continue

        workflow_name = name[: -len(".properties.json")]
        if (
            f"{workflow_name}.yml" not in files
            and f"{workflow_name}.yaml" not in files
        ):
            raise ValueError(f"metadata has no matching workflow: {name}")

        try:
            metadata = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSON in {name}: {error}") from error

        if not isinstance(metadata, dict):
            raise ValueError(f"metadata must be a JSON object: {name}")

        icon_name = metadata.get("iconName")
        if icon_name is not None:
            if not isinstance(icon_name, str) or not icon_name:
                raise ValueError(f"iconName must be a non-empty string: {name}")
            if not icon_name.startswith("octicon "):
                icon_file = f"{icon_name}.svg"
                if icon_file not in files:
                    raise ValueError(
                        f"metadata references missing icon {icon_file}: {name}"
                    )


def sync_catalog(
    source: Path,
    target: Path,
    template_names: tuple[str, ...] | None = None,
) -> dict[str, list[str]]:
    source_files = collect_publishable(source, template_names)
    target.mkdir(parents=True, exist_ok=True)

    target_files = {
        path.name: path
        for path in target.iterdir()
        if is_publishable(path)
    }

    updated: list[str] = []
    unchanged: list[str] = []
    removed: list[str] = []

    for name, source_path in sorted(source_files.items()):
        target_path = target / name
        source_content = source_path.read_bytes()

        if target_path.is_file() and target_path.read_bytes() == source_content:
            unchanged.append(name)
            continue

        shutil.copyfile(source_path, target_path)
        updated.append(name)

    for name, target_path in sorted(target_files.items()):
        if name in source_files:
            continue
        target_path.unlink()
        removed.append(name)

    return {
        "updated": updated,
        "unchanged": unchanged,
        "removed": removed,
    }


def check_catalog(
    source: Path,
    target: Path,
    template_names: tuple[str, ...] | None = None,
) -> None:
    source_files = collect_publishable(source, template_names)
    target_files = {
        path.name: path
        for path in target.iterdir()
        if is_publishable(path)
    } if target.is_dir() else {}

    problems: list[str] = []

    for name, source_path in sorted(source_files.items()):
        target_path = target_files.get(name)
        if target_path is None:
            problems.append(f"missing from catalog: {name}")
        elif target_path.read_bytes() != source_path.read_bytes():
            problems.append(f"catalog file differs: {name}")

    for name in sorted(set(target_files) - set(source_files)):
        problems.append(f"stale catalog file: {name}")

    if problems:
        raise ValueError("; ".join(problems))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("sync", "check"))
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    try:
        template_names = (
            load_catalog_manifest(args.manifest)
            if args.manifest is not None
            else None
        )

        if args.command == "sync":
            report = sync_catalog(args.source, args.target, template_names)
            if args.report:
                args.report.write_text(
                    json.dumps(report, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0

        check_catalog(args.source, args.target, template_names)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
