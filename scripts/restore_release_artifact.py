#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen
from zipfile import ZipFile



class CrossHostAuthStrippingRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is None:
            return None
        if urlparse(req.full_url).netloc != urlparse(newurl).netloc:
            redirected.remove_header("Authorization")
            redirected.remove_header("X-GitHub-Api-Version")
            redirected.remove_header("Accept")
        return redirected

def select_artifact(payload: object, name: str, expected_head_sha: str | None) -> dict[str, object]:
    if not isinstance(payload, dict) or not isinstance(payload.get("artifacts"), list):
        raise RuntimeError("GitHub returned an invalid artifact listing")

    candidates: list[dict[str, object]] = []
    for item in payload["artifacts"]:
        if not isinstance(item, dict):
            continue
        if item.get("name") != name or item.get("expired") is True:
            continue
        workflow_run = item.get("workflow_run")
        if expected_head_sha:
            if not isinstance(workflow_run, dict) or workflow_run.get("head_sha") != expected_head_sha:
                continue
        candidates.append(item)

    if not candidates:
        suffix = f" for head {expected_head_sha}" if expected_head_sha else ""
        raise RuntimeError(f"Actions artifact {name!r}{suffix} was not found")

    candidates.sort(
        key=lambda item: (str(item.get("created_at", "")), int(item.get("id", 0))),
        reverse=True,
    )
    return candidates[0]


def safe_extract_zip(data: bytes, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()

    with ZipFile(io.BytesIO(data)) as archive:
        for entry in archive.infolist():
            relative = Path(entry.filename)
            if relative.is_absolute() or ".." in relative.parts:
                raise RuntimeError(f"unsafe artifact path: {entry.filename}")
            target = (destination / relative).resolve()
            try:
                target.relative_to(root)
            except ValueError as error:
                raise RuntimeError(f"unsafe artifact path: {entry.filename}") from error

        archive.extractall(destination)


def request_json(url: str, token: str) -> object:
    request = Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "LibreCodeCoop/github-workflows",
    })
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def request_bytes(url: str, token: str) -> bytes:
    request = Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "LibreCodeCoop/github-workflows",
    })
    opener = build_opener(CrossHostAuthStrippingRedirectHandler())
    with opener.open(request, timeout=60) as response:
        return response.read()


def validate_workflow_run(payload: object, expected_event: str | None, expected_workflow_path: str | None) -> None:
    if not isinstance(payload, dict):
        raise RuntimeError("GitHub returned an invalid workflow run")
    if expected_event and payload.get("event") != expected_event:
        raise RuntimeError(f"artifact workflow event {payload.get('event')!r} does not match {expected_event!r}")
    if expected_workflow_path and payload.get("path") != expected_workflow_path:
        raise RuntimeError(f"artifact workflow path {payload.get('path')!r} does not match {expected_workflow_path!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--expected-head-sha", default="")
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--expected-event", default="")
    parser.add_argument("--expected-workflow-path", default="")
    parser.add_argument("--api-url", default=os.environ.get("GITHUB_API_URL", "https://api.github.com"))
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "")
    if token.strip() == "":
        parser.error("GITHUB_TOKEN must not be empty")

    listing_url = (
        f"{args.api_url.rstrip('/')}/repos/{args.repository}/actions/artifacts"
        f"?name={quote(args.name, safe='')}&per_page=100"
    )
    artifact = select_artifact(
        request_json(listing_url, token),
        args.name,
        args.expected_head_sha or None,
    )
    workflow_run = artifact.get("workflow_run")
    run_id = workflow_run.get("id") if isinstance(workflow_run, dict) else None
    if args.expected_event or args.expected_workflow_path:
        if not isinstance(run_id, int):
            parser.error("GitHub returned an artifact without workflow run identity")
        run_url = f"{args.api_url.rstrip('/')}/repos/{args.repository}/actions/runs/{run_id}"
        validate_workflow_run(
            request_json(run_url, token),
            args.expected_event or None,
            args.expected_workflow_path or None,
        )

    archive_url = artifact.get("archive_download_url")
    if not isinstance(archive_url, str) or archive_url == "":
        parser.error("GitHub returned an artifact without archive_download_url")

    safe_extract_zip(request_bytes(archive_url, token), args.destination)

    print(json.dumps({
        "artifact_id": artifact.get("id"),
        "workflow_run_id": run_id,
        "name": args.name,
        "created_at": artifact.get("created_at"),
    }, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
