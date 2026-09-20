<!--
SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Architecture

## Responsibility boundary

`github-workflows` owns reusable CI and release automation.

It does not manage repository rulesets. That responsibility belongs to
`LibreCodeCoop/github-governance`.

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
generated template
        ↓
tests + actionlint + zizmor
        ↓
versioned release
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
