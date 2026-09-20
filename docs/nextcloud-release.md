<!--
SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Nextcloud release planning

The reusable release-plan workflow is intentionally non-mutating. It validates
release prerequisites before any tag, GitHub Release, signing or App Store
publication occurs.

## Architecture

The reusable workflow owns orchestration concerns: permissions, runner selection
and checking out the caller plus the workflow tooling repository.

The release-plan operation itself is exposed as the local composite action
`actions/release-plan`. The action maps its declared inputs to a small,
namespaced environment contract and invokes `scripts/release_plan.py`.

Business rules, input parsing, GitHub API checks, exit status and step-summary
rendering live in the Python script and are covered by unit tests. The workflow
does not contain release decision logic.

This follows GitHub's distinction between reusable workflows, which reuse whole
workflow/job structures, and composite actions, which encapsulate a reusable
sequence of steps within a job.

## Checks

The first implementation validates:

- semantic release version in `MAJOR.MINOR.PATCH` form;
- execution from the declared stable branch;
- `appinfo/info.xml` version matches the requested release;
- changelog contains a level-2 section for the requested version;
- optional milestone exists, is closed and has zero open issues;
- optional GitHub blocker queries return zero open issues or pull requests.

Blocker queries are caller-owned. This keeps project conventions out of the
shared workflow. A caller can model pending backports with a label query without
making that label part of the reusable workflow contract.

## Example caller

```yaml
jobs:
  release-plan:
    uses: LibreCodeCoop/github-workflows/.github/workflows/release-plan.yml@<full-release-sha> # v0.1.0
    with:
      version: 16.0.0
      stable_branch: stable36
      milestone: 16.0.0
      blocker_queries: '["label:\"backport pending\""]'
```

The workflow only needs read permissions. Signing keys and App Store tokens are
deliberately not accepted by the planning stage.

Publication will be implemented as a separate privileged workflow after the
planning contract is proven with LibreSign and at least one additional app.
