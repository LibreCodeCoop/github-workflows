<!--
SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# GitHub Workflows

Reusable, testable GitHub workflows for organizations that want consistent CI
and release automation without copying opaque YAML between repositories.

This project keeps reusable workflow logic independent from
[GitHub Governance](https://github.com/LibreCodeCoop/github-governance):
governance manages repository rulesets, while this repository manages reusable
workflows and reproducible upstream workflow adaptations.

## Why use it

- **Reusable automation:** consume shared workflows instead of maintaining copies.
- **Reproducible upstream imports:** source files are tied to immutable upstream commits and SHA-256 hashes.
- **Reviewable downstream changes:** local adaptations are explicit and testable.
- **Security-first defaults:** third-party Actions are pinned to immutable commit SHAs.
- **Versioned consumption:** releases are referenced by immutable SHA with a human-readable version comment.

## Current scope

The first target is reusable automation for Nextcloud applications, with
LibreSign as the first production consumer.

The repository is intentionally product-agnostic. LibreSign and Nextcloud are
reference consumers and upstream sources, not hard-coded engine concepts.

## Repository layout

- `templates/` — generated or maintained reusable workflow templates.
- `upstream/` — immutable source manifests.
- `patches/` — explicit downstream adaptations.
- `scripts/` — deterministic synchronization/check tooling.
- `tests/` — tests for synchronization and template behavior.
- `docs/` — architecture, adoption and security guidance.

## Development

Run:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/sync_upstream.py check upstream/sources.json
```

See [Architecture](docs/architecture.md) and
[Upstream workflow model](docs/upstream-workflows.md).

## Security

Workflow code executes inside consumers' CI environments. Review
[SECURITY.md](SECURITY.md) before adoption.

GitHub Workflows is free software licensed under AGPL-3.0-or-later and follows
the REUSE specification.
