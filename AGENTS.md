<!--
SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Agent guidance

## Purpose

This repository owns reusable GitHub Actions orchestration, shared workflow templates, catalog generation and consumer synchronization for LibreCode projects and downstream integrations.

## Boundaries

- Workflow YAML orchestrates; reusable release business policy belongs in `LibreCodeCoop/release-tool`.
- Keep consumer-specific differences in explicit inputs, configuration or consumer-local patches.
- Do not duplicate release policy from `release-tool` into shell/YAML.
- Materialized templates under the catalog are generated/published artifacts; preserve their source and patch provenance.
- The release automation architecture is tracked by issue #70 and the repository documentation.

## Generated and managed files

- `upstream/vendor/**` is synchronized from pinned upstream sources.
- `workflow-templates/**` may be rendered from reusable workflows/upstream plus LibreCode patches.
- Consumer `.github/actions-lock.txt` files are managed by `actions/sync-workflows`.
- Do not edit generated outputs without changing their source/patch contract.

## Quality gates

Before merging relevant changes, run or rely on the repository CI for:

- Python unit tests;
- actionlint;
- zizmor;
- REUSE compliance;
- workflow policy checks;
- setup/release smoke tests where affected.

## Security

- Pin third-party actions to immutable commit SHAs.
- Keep permissions least-privilege per job/stage.
- Do not expose organization or consumer credentials.
- Do not execute untrusted pull-request content in privileged contexts.
- Cross-repository mutations should use short-lived GitHub App installation tokens.

## SPDX / REUSE

New files must follow the repository SPDX/REUSE policy. Code and LibreCode-owned automation use AGPL-3.0-or-later unless an imported/upstream file retains its original compatible license.
