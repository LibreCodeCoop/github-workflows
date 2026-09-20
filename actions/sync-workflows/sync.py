#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

LOCK_HEADER = (
    "# SPDX-FileCopyrightText: 2025 Nextcloud GmbH and Nextcloud contributors\n"
    "# SPDX-" + "License-Identifier: MIT\n"
)


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest()


def parse_lock(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}

    entries: dict[str, str] = {}
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"invalid lock entry at line {line_number}")

        digest, workflow = parts
        if (
            len(digest) != 32
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise ValueError(f"invalid MD5 at line {line_number}")

        if workflow in entries:
            raise ValueError(f"duplicate lock entry: {workflow}")
        entries[workflow] = digest

    return entries


def write_lock(path: Path, entries: dict[str, str]) -> None:
    lines = [LOCK_HEADER.rstrip("\n"), ""]
    lines.extend(f"{entries[name]} {name}" for name in sorted(entries))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def apply_patch(target_root: Path, target_file: Path) -> tuple[bool, str]:
    patch_file = Path(f"{target_file}.patch")
    if not patch_file.is_file():
        return True, ""

    relative_patch = patch_file.relative_to(target_root)
    result = subprocess.run(
        ["patch", "--batch", "--forward", "-p1"],
        cwd=target_root,
        input=patch_file.read_bytes(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = result.stdout.decode("utf-8", errors="replace").strip()
    if result.returncode == 0:
        return True, f"Patch applied: {relative_patch}"

    return False, f"Patch failed: {relative_patch}\n{output}"


def workflow_files(source: Path) -> list[Path]:
    return sorted(
        path
        for path in source.iterdir()
        if path.is_file() and path.suffix in {".yml", ".yaml"}
    )


def sync(
    source: Path,
    target: Path,
    lock_path: Path,
) -> dict[str, object]:
    if not source.is_dir():
        raise ValueError(f"source directory does not exist: {source}")
    if not target.is_dir():
        raise ValueError(f"target directory does not exist: {target}")

    entries = parse_lock(lock_path)
    updated: list[str] = []
    unchanged: list[str] = []
    skipped: list[str] = []
    failed: list[str] = []
    details: list[str] = []

    for source_file in workflow_files(source):
        name = source_file.name
        target_file = target / ".github/workflows" / name

        if not target_file.is_file():
            skipped.append(name)
            continue

        new_version = md5(source_file)
        locked_version = entries.get(name, "")

        if locked_version == new_version:
            unchanged.append(name)
            continue

        shutil.copyfile(source_file, target_file)
        patch_ok, patch_message = apply_patch(target, target_file)
        entries[name] = new_version
        updated.append(name)

        if patch_message:
            details.append(f"- {name}: {patch_message}")
        if not patch_ok:
            failed.append(name)

    if updated or not lock_path.is_file():
        write_lock(lock_path, entries)

    return {
        "changed": bool(updated),
        "patch_failed": bool(failed),
        "updated": updated,
        "unchanged": unchanged,
        "skipped": skipped,
        "failed": failed,
        "details": details,
    }


def render_summary(report: dict[str, object]) -> str:
    lines = [
        "## Workflow synchronization",
        "",
        f"- Updated: {len(report['updated'])}",
        f"- Unchanged: {len(report['unchanged'])}",
        f"- Skipped: {len(report['skipped'])}",
        f"- Patch failures: {len(report['failed'])}",
    ]

    details = report["details"]
    if details:
        lines.extend(["", "### Details", "", *details])

    lines.append("")
    return "\n".join(lines)


def write_output(name: str, value: str) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--lock-file", default=".github/actions-lock.txt")
    args = parser.parse_args()

    try:
        source = args.source.resolve()
        target = args.target.resolve()
        lock_path = target / args.lock_file

        report = sync(source, target, lock_path)

        summary = render_summary(report)
        summary_root = Path(os.environ.get("RUNNER_TEMP", target / ".github"))
        summary_path = summary_root / "workflow-sync-summary.md"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(summary, encoding="utf-8")

        write_output("changed", str(report["changed"]).lower())
        write_output("patch_failed", str(report["patch_failed"]).lower())
        write_output("updated", json.dumps(report["updated"], separators=(",", ":")))
        write_output("failed", json.dumps(report["failed"], separators=(",", ":")))
        write_output("summary", summary)
        write_output("summary_file", str(summary_path))

        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError) as error:
        parser.error(str(error))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
