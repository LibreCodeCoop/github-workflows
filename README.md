<!--
SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# GitHub Workflows

Managed, testable GitHub workflow templates and supporting Actions for organizations
that want consistent CI without copying opaque YAML between repositories.

This project keeps workflow distribution independent from
[GitHub Governance](https://github.com/LibreCodeCoop/github-governance):
governance manages repository rulesets, while this repository manages workflow
sources, adaptations, tests and publication.

## Why use it

- **Reproducible upstream imports:** source files are tied to immutable upstream commits and SHA-256 hashes.
- **Reviewable downstream changes:** LibreCode adaptations are explicit patches.
- **Materialized consumer workflows:** repositories keep normal local GitHub workflows instead of opaque remote callers.
- **Automated updates:** consumers receive reviewable pull requests from the organization catalog.
- **Local customization:** consumer-specific differences live in `.github/workflows/<workflow>.patch`.
- **Security-first defaults:** external Actions are pinned and checked by policy CI.

## Distribution model

`LibreCodeCoop/github-workflows` is the source of truth.

`LibreCodeCoop/.github` is the organization catalog used by GitHub's
**Actions → New workflow** UI.

Consumer repositories install full workflow files. Their local
`sync-workflow-templates.yml` periodically invokes
`actions/sync-workflows`, which:

- updates workflows already installed in the repository;
- applies local workflow patches;
- records catalog versions in `.github/actions-lock.txt`;
- refuses to overwrite unexplained local divergence;
- opens reviewable update pull requests through the caller workflow.

## Repository layout

- `workflow-templates/` — generated organization workflow templates.
- `actions/` — tested Actions used by the workflow platform.
- `upstream/` — immutable source manifests and vendored upstream files.
- `patches/` — explicit organization-level adaptations.
- `scripts/` — deterministic synchronization and policy tooling.
- `tests/` — tests for synchronization, rendering and policy behavior.
- `docs/` — architecture, security and adoption decisions.

## Release automation for Nextcloud apps

The repository also publishes tested release orchestration actions backed by [LibreCodeCoop/release-tool](https://github.com/LibreCodeCoop/release-tool).

Maintainers of Nextcloud apps can use them to replace repeatable release checklists with a reviewable flow:

**prepare plan → generated PR → maintainer merge → release draft → maintainer publish → verification**

See [Adopting the release automation](docs/release-automation.md).

## Development

Run:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/sync_upstream.py check upstream/sources.json
python3 scripts/render_upstream.py check upstream/templates.json
python3 scripts/check_workflow_policy.py
```

See [Architecture](docs/architecture.md),
[Upstream workflow model](docs/upstream-workflows.md),
[GitHub Actions security policy](docs/security-policy.md) and
[Dependency update policy](docs/dependency-update-policy.md).

## Security

Workflow code executes inside consumers' CI environments. Review
[SECURITY.md](SECURITY.md) before adoption.

GitHub Workflows is free software licensed under AGPL-3.0-or-later and follows
the REUSE specification.
