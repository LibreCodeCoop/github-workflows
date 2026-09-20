<!--
SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Architecture

## Responsibility boundary

`github-workflows` is the source of truth for imported workflow adaptations,
generated organization templates and tested helper Actions.

`LibreCodeCoop/.github` is the organization-facing catalog. It is a distribution
target, not an editing source.

Repository rulesets remain the responsibility of
`LibreCodeCoop/github-governance`.

Consumer repositories own:

- which catalog workflows they install;
- consumer-specific workflow patches;
- credentials and protected environments;
- branch policy;
- the final review and merge of workflow-update pull requests.

## Upstream workflow pipeline

```text
immutable upstream commit
        ↓
source URL + SHA-256
        ↓
vendored upstream file
        ↓
explicit LibreCode patch
        ↓
generated workflow template
        ↓
tests + actionlint + zizmor + workflow policy
        ↓
LibreCodeCoop/.github catalog
```

The source manifest is authoritative. A network response that does not match the
recorded SHA-256 fails closed.

When a refresh resolves a newer upstream commit but the file bytes are unchanged,
the existing immutable pin is preserved to avoid meaningless pin-only pull requests.

## Consumer update pipeline

```text
LibreCodeCoop/.github catalog
        ↓
consumer sync-workflow-templates.yml
        ↓
LibreCodeCoop/github-workflows/actions/sync-workflows
        ↓
compare .github/actions-lock.txt
        ↓
copy changed catalog workflow
        ↓
apply optional consumer-local <workflow>.patch
        ↓
reviewable consumer pull request
```

Only workflows already installed in the consumer are managed. The sync Action does
not maintain a central consumer registry.

The lock records the catalog version before consumer-local patching. If a local file
cannot be explained by the catalog plus its local patch, synchronization stops rather
than overwriting the divergence.

A local patch that no longer applies is surfaced for human intervention.

## Organization patches vs consumer patches

Organization-level differences from Nextcloud belong in
`patches/nextcloud/*.patch` and should remain minimal.

Consumer-specific differences belong beside the installed workflow:

```text
.github/workflows/example.yml
.github/workflows/example.yml.patch
```

Do not move a consumer-only branch list, product dependency or credential assumption
into the organization template.

## Distribution decision

The default model is a materialized workflow template because it remains visible,
reviewable and native to the consumer repository.

A custom Action is appropriate when substantial deterministic logic can be extracted
from YAML and tested independently, as with `actions/sync-workflows`.

Reusable workflows are not the default distribution model. Introduce one only when
GitHub Actions semantics clearly benefit from centralized execution and the consumer
still retains an explicit, reviewable interface.

## Credential-sensitive automation

Catalog publication does not imply that every workflow is safe to install everywhere.
Dependency approval, auto-merge and release workflows follow the documented security
and credential policies and may intentionally remain repository-local.
