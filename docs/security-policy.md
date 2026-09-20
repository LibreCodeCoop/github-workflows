<!--
SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# GitHub Actions security policy

This repository publishes workflow templates that execute inside consumer repositories.
The baseline policy is intentionally small, objective and testable.

## Mandatory rules

Published templates and this repository's own workflows must:

- pin external GitHub Actions to a full 40-character commit SHA;
- keep a human-readable version comment next to the pin when a stable release is known;
- configure `actions/checkout` with `persist-credentials: false`;
- avoid `permissions: write-all`;
- use explicit least-privilege workflow or job permissions.

The first three mechanically enforceable rules are checked by
`scripts/check_workflow_policy.py`. Existing actionlint and zizmor checks remain
responsible for syntax, expression and broader workflow security analysis.

## Exceptions

An exception must be explicit in the pull request that introduces it and must explain:

1. why the workflow cannot use the mandatory rule;
2. the smallest additional permission or credential needed;
3. how the risk is constrained;
4. how the exception will be tested.

Do not encode permanent organization-name bypasses when a generic permission or
capability check can express the same requirement.

## Credentials

Consumer repositories own runtime credentials and protected environments.
Organization-level GitHub App credentials may be used for public consumer repositories
when the organization plan allows them.

Mutating automation must prefer a GitHub App over personal access tokens. Personal or
bot PATs are a last resort and require an explicit documented exception.

## Governance

`github-workflows` validates workflow content. Repository rulesets and required-check
enforcement belong in `LibreCodeCoop/github-governance`.

A workflow policy check becomes a candidate required check only after it is stable on
the default branch and does not produce false positives on the published catalog.
