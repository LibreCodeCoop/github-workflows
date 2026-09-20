<!--
SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Upstream workflow model

Upstream files are declared in `upstream/sources.json`.

Each entry contains:

- `name`: stable local identifier;
- `repository`, `ref` and `path`: optional tracking metadata used only to discover newer upstream revisions;
- `url`: raw file URL pinned to an immutable upstream commit;
- `sha256`: expected SHA-256 of the downloaded bytes;
- `destination`: repository-relative vendored destination.

The tracking ref can be mutable. The effective source cannot: after refresh, the
manifest is rewritten to a full commit SHA and content hash before the vendored
file is accepted.

Example:

```json
{
  "sources": [
    {
      "name": "example",
      "repository": "example/project",
      "ref": "main",
      "path": ".github/workflows/example.yml",
      "url": "https://raw.githubusercontent.com/example/project/<commit>/.github/workflows/example.yml",
      "sha256": "<64 lowercase hex characters>",
      "destination": "upstream/vendor/example/example.yml"
    }
  ]
}
```

## Commands

Synchronize declared immutable sources:

```bash
python3 scripts/sync_upstream.py sync upstream/sources.json
```

Verify committed vendored files without modifying them:

```bash
python3 scripts/sync_upstream.py check upstream/sources.json
```

Resolve tracked refs to their latest commit, recompute SHA-256 and update the
vendored files:

```bash
python3 scripts/sync_upstream.py refresh upstream/sources.json
```

The scheduled `refresh-upstream.yml` workflow runs this refresh weekly, validates
the result and opens a pull request when upstream changed.

A dedicated `WORKFLOW_UPDATE_TOKEN` secret is required for pull-request creation.
Using only the workflow's `GITHUB_TOKEN` would prevent the resulting pull request
from triggering the normal CI workflows. The refresh itself only uses the
read-only `GITHUB_TOKEN` to resolve public upstream commits.

Both `sync` and `check` verify the recorded source hash before accepting
content. `refresh` only records bytes fetched from the exact commit it resolved.

Patch application is intentionally a separate layer: upstream bytes remain
verbatim under `upstream/vendor/`, while downstream adaptations should be stored
as reviewable patches and rendered into generated templates.
