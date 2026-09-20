<!--
SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Architecture

## Responsibility boundary

`github-workflows` is the source of truth for reusable CI, imported workflow adaptations, generated workflow templates and release automation.

`LibreCodeCoop/.github` is the organization-facing catalog. Generated workflow templates can be published there so developers can discover them through GitHub's **Actions → New workflow** experience. The catalog is a distribution target, not the editing source.

Repository rulesets remain the responsibility of `LibreCodeCoop/github-governance`.

Consumer repositories own:

- credentials and protected environments;
- product-specific configuration;
- the decision to invoke a mutating workflow;
- immutable pins to released workflow revisions.

## Upstream workflow pipeline

An imported workflow follows this pipeline:

```text
immutable upstream commit
        ↓
source URL + SHA-256 in manifest
        ↓
deterministic fetch
        ↓
hash verification
        ↓
explicit downstream patches
        ↓
generated `workflow-templates/` artifact
        ↓
tests + actionlint + zizmor
        ↓
publish catalog copy to `LibreCodeCoop/.github`
        ↓
versioned release / consumer update
```

The source manifest is authoritative. A network response that does not match the
recorded SHA-256 fails closed.

## Generated files

Generated templates must not be edited directly. Changes should come from:

1. an upstream source revision change; or
2. an explicit downstream patch.

CI should detect when regenerated output differs from committed output.

## Release automation

Release automation is split into two stages:

- **plan:** non-mutating validation and release proposal;
- **apply:** explicit mutation and publication.

Credentials remain in the consumer repository or protected environment.

## Developer experience

The distribution model has two complementary entry points:

1. **Discovery / first install:** `LibreCodeCoop/.github/workflow-templates/` provides the GitHub-native template cards, metadata and optional icons.
2. **Ongoing updates:** consumer repositories receive reviewable update pull requests generated from the tested templates in this repository.

When a workflow can be expressed as a thin caller of a reusable workflow, prefer that model because fixes remain centralized. When GitHub Actions semantics require a full installed workflow, publish the generated workflow template and keep its downstream differences as explicit patches here.
