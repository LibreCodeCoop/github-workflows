<!--
SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Upstream workflow model

Upstream files are declared in `upstream/sources.json`.

Each entry contains:

- `name`: stable local identifier;
- `url`: raw file URL pinned to an immutable upstream commit;
- `sha256`: expected SHA-256 of the downloaded bytes;
- `destination`: repository-relative generated destination.

Example:

```json
{
  "sources": [
    {
      "name": "example",
      "url": "https://raw.githubusercontent.com/example/project/<commit>/.github/workflows/example.yml",
      "sha256": "<64 lowercase hex characters>",
      "destination": "templates/example.yml"
    }
  ]
}
```

## Commands

Synchronize declared sources:

```bash
python3 scripts/sync_upstream.py sync upstream/sources.json
```

Verify committed generated files without modifying them:

```bash
python3 scripts/sync_upstream.py check upstream/sources.json
```

Both commands verify the source hash before accepting content.

Patch application will be introduced with the first real upstream template so
the patch interface is designed against an actual workflow rather than a
hypothetical format.
