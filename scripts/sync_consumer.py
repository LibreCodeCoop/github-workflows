#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

LOCK_HEADER = (
    "# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors\n"
    "# SPDX-" + "License-Identifier: MIT\n"
)


@dataclass(frozen=True)
class Consumer:
    repository: str
    workflows: tuple[str, ...]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_consumers(path: Path) -> list[Consumer]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("consumer manifest must be a JSON object")

    raw_consumers = payload.get("consumers")
    if not isinstance(raw_consumers, list):
        raise ValueError("consumer manifest must contain a consumers array")

    consumers: list[Consumer] = []
    seen: set[str] = set()

    for index, raw in enumerate(raw_consumers):
        if not isinstance(raw, dict):
            raise ValueError(f"consumers[{index}] must be an object")

        repository = raw.get("repository")
        workflows = raw.get("workflows")

        if not isinstance(repository, str) or "/" not in repository:
            raise ValueError(f"consumers[{index}].repository must be owner/name")
        if repository in seen:
            raise ValueError(f"duplicate consumer repository: {repository}")
        seen.add(repository)

        if (
            not isinstance(workflows, list)
            or not workflows
            or not all(isinstance(item, str) and item for item in workflows)
        ):
            raise ValueError(
                f"consumers[{index}].workflows must be a non-empty array of names"
            )

        if len(set(workflows)) != len(workflows):
            raise ValueError(f"duplicate workflow in consumer {repository}")

        for workflow in workflows:
            workflow_path = Path(workflow)
            if (
                workflow_path.name != workflow
                or workflow_path.suffix not in {".yml", ".yaml"}
            ):
                raise ValueError(
                    f"invalid workflow name for {repository}: {workflow}"
                )

        consumers.append(
            Consumer(repository=repository, workflows=tuple(sorted(workflows)))
        )

    return consumers


def matrix(consumers: list[Consumer]) -> dict[str, list[dict[str, object]]]:
    return {
        "include": [
            {
                "repository": consumer.repository,
                "repository_name": consumer.repository.split("/", 1)[1],
                "workflows": list(consumer.workflows),
            }
            for consumer in consumers
        ]
    }


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
            len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise ValueError(f"invalid SHA-256 at line {line_number}")

        if workflow in entries:
            raise ValueError(f"duplicate lock entry: {workflow}")
        entries[workflow] = digest

    return entries


def write_lock(path: Path, entries: dict[str, str]) -> None:
    lines = [LOCK_HEADER.rstrip("\n"), ""]
    lines.extend(f"{entries[name]} {name}" for name in sorted(entries))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def sync_consumer(
    source_dir: Path,
    target_dir: Path,
    workflows: tuple[str, ...],
    lock_path: Path,
) -> dict[str, object]:
    lock_entries = parse_lock(lock_path)
    results: list[dict[str, str]] = []
    failed = False

    for workflow in workflows:
        source = source_dir / workflow
        target = target_dir / ".github/workflows" / workflow

        if not source.is_file():
            results.append(
                {
                    "workflow": workflow,
                    "status": "failed",
                    "message": "source template does not exist",
                }
            )
            failed = True
            continue

        source_hash = sha256(source)
        locked_hash = lock_entries.get(workflow)

        if locked_hash is None:
            if target.is_file() and sha256(target) != source_hash:
                results.append(
                    {
                        "workflow": workflow,
                        "status": "failed",
                        "message": (
                            "existing workflow is not managed yet and differs "
                            "from the current template"
                        ),
                    }
                )
                failed = True
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
            lock_entries[workflow] = source_hash
            results.append(
                {
                    "workflow": workflow,
                    "status": "adopted",
                    "message": "workflow adopted into managed synchronization",
                }
            )
            continue

        if not target.is_file():
            results.append(
                {
                    "workflow": workflow,
                    "status": "failed",
                    "message": "managed workflow was deleted locally",
                }
            )
            failed = True
            continue

        current_hash = sha256(target)
        if current_hash != locked_hash:
            results.append(
                {
                    "workflow": workflow,
                    "status": "failed",
                    "message": "local workflow diverged from its managed lock",
                }
            )
            failed = True
            continue

        if source_hash == locked_hash:
            results.append(
                {
                    "workflow": workflow,
                    "status": "unchanged",
                    "message": "workflow is already current",
                }
            )
            continue

        target.write_bytes(source.read_bytes())
        lock_entries[workflow] = source_hash
        results.append(
            {
                "workflow": workflow,
                "status": "updated",
                "message": "workflow updated to the current template",
            }
        )

    write_lock(lock_path, lock_entries)

    return {
        "ok": not failed,
        "results": results,
    }


def render_pull_request_body(repository: str, report: dict[str, object]) -> str:
    lines = [
        "Automated synchronization from LibreCodeCoop/github-workflows.",
        "",
        f"Consumer: {repository}",
        "",
        "## Workflow status",
        "",
    ]

    icons = {
        "adopted": "OK",
        "updated": "UPDATED",
        "unchanged": "UNCHANGED",
        "failed": "FAILED",
    }

    for item in report["results"]:
        status = item["status"]
        lines.append(
            f"- {icons[status]} {item['workflow']} - {status}: {item['message']}"
        )

    lines.extend(
        [
            "",
            "Managed workflow files are updated only when their current SHA-256 "
            "matches the previously recorded lock. Local divergence is never "
            "overwritten silently.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    matrix_parser = subparsers.add_parser("matrix")
    matrix_parser.add_argument("manifest", type=Path)

    sync_parser = subparsers.add_parser("sync")
    sync_parser.add_argument("manifest", type=Path)
    sync_parser.add_argument("repository")
    sync_parser.add_argument("source_dir", type=Path)
    sync_parser.add_argument("target_dir", type=Path)
    sync_parser.add_argument("--report", type=Path)
    sync_parser.add_argument("--body", type=Path)

    args = parser.parse_args()

    try:
        consumers = load_consumers(args.manifest)

        if args.command == "matrix":
            print(json.dumps(matrix(consumers), separators=(",", ":")))
            return 0

        consumer = next(
            (item for item in consumers if item.repository == args.repository),
            None,
        )
        if consumer is None:
            raise ValueError(f"consumer is not declared: {args.repository}")

        lock_path = args.target_dir / ".github/librecode-workflows.lock"
        report = sync_consumer(
            args.source_dir,
            args.target_dir,
            consumer.workflows,
            lock_path,
        )

        if args.report:
            args.report.write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        if args.body:
            args.body.write_text(
                render_pull_request_body(args.repository, report),
                encoding="utf-8",
            )

        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ok"] else 1

    except (OSError, ValueError) as error:
        parser.error(str(error))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
