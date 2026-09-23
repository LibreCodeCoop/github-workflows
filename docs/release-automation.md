<!--
SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Adopting the release automation

This repository contains the GitHub Actions orchestration for [LibreCodeCoop/release-tool](https://github.com/LibreCodeCoop/release-tool).

It is intended for projects that want release policy to be testable and deterministic without embedding a large release implementation in every consumer workflow.

## What the shared actions provide

The main release actions are:

- `actions/release-prepare` — build/validate a release plan, authorize the requester, create or reuse the deterministic preparation PR, and persist the release contracts;
- `actions/release-post-merge` — restore the original preparation state, authorize the merger, revalidate the merged release, synchronize release history, transition milestones, and create/update the GitHub Release draft;
- `actions/release-publication` — verify the published release against the configured publisher workflow and expected asset.

The release engine itself lives in `LibreCodeCoop/release-tool`. These actions intentionally remain orchestration.

## Before adopting

Read the Release Tool [Getting started guide](https://github.com/LibreCodeCoop/release-tool/blob/main/docs/getting-started.md) first.

Your repository should already know:

- which stable branch is being released;
- where the authoritative version lives;
- how changelog history is stored;
- how packages are built and published;
- how release milestones are named.

Add `.nextcloud-release.yml` before adding the workflow.

## GitHub App

Mutating stages use short-lived installation tokens.

External organizations must create and install their own GitHub App. Do not expect the LibreCode App to be installed in another organization. Follow the [GitHub App setup guide](https://github.com/LibreCodeCoop/release-tool/blob/main/docs/github-app.md) for the exact registration settings, repository permissions, installation scope, private-key generation, and Actions secret configuration.

The consumer passes:

- an App slug;
- the App private key stored as an Actions secret.

The actions resolve the public client id from the slug and request only the permissions needed by each stage.

## Minimal workflow shape

A consumer normally needs one workflow with three events:

```yaml
name: Prepare release

on:
  workflow_dispatch:
    inputs:
      branch:
        description: Stable branch to release, e.g. stable35
        required: true
        type: string
      version:
        description: Optional explicit version
        required: false
        type: string
      channel:
        required: true
        default: final
        type: choice
        options: [alpha, beta, rc, final]

  pull_request_target:
    types: [closed]

  release:
    types: [published]

permissions: {}

concurrency:
  group: release-automation-${{ github.repository }}
  cancel-in-progress: false
```

The jobs then call the three shared actions.

Always pin shared actions to an immutable commit SHA:

```yaml
uses: LibreCodeCoop/github-workflows/actions/release-prepare@<PINNED_SHA> # vX.Y.Z
```

Do not use `main` in production release automation.

## Preparation job

The preparation job should:

1. run only for `workflow_dispatch`;
2. check out the requested branch/ref;
3. fetch the release branch and tags;
4. call `actions/release-prepare`.

The action expects:

- branch/ref/version/channel inputs;
- `.nextcloud-release.yml`;
- requesting actor;
- the caller `GITHUB_TOKEN` for read-only checks;
- the GitHub App private key for mutations.

## Post-merge job

The post-merge job uses `pull_request_target: closed` because generated preparation commits intentionally contain `[skip ci]`.

Do not run this job for arbitrary closed PRs.

Use guards equivalent to:

```yaml
if: >-
  github.event_name == 'pull_request_target' &&
  github.event.pull_request.merged == true &&
  startsWith(github.event.pull_request.head.ref, 'release-tool/') &&
  contains(github.event.pull_request.body, '<!-- release-tool:preparation ')
```

Check out the trusted base/release branch, not the PR head.

Then call `actions/release-post-merge` with:

- merged preparation PR number;
- merger login;
- consumer config path;
- prepare workflow path;
- tokens/credentials.

## Publication verification

On `release: published`, check out the published tag and call `actions/release-publication`.

The verifier confirms the deterministic signals owned by the repository:

- release identity;
- expected publisher workflow;
- expected asset.

Public App Store visibility is secondary because public indexes can be cached or rate-limited.

## Human gates

The automation deliberately stops at two points:

- the generated preparation PR must be reviewed and merged;
- the generated GitHub Release draft must be reviewed and published.

This prevents release automation from turning repository state changes into an unattended deployment pipeline.

## Auditability

The actions write concise GitHub step summaries and persist full machine-readable release contracts as Actions artifacts.

The summary is for operators. The artifacts are the durable audit state.

A normal release records enough information to answer:

- who requested preparation;
- which branch/SHA was planned;
- which release-tool version was used;
- which PR represented the preparation;
- which exact commit became the release target;
- which history synchronization PRs were created;
- which milestone transition was applied;
- which GitHub Release was created.

## Reference consumer

LibreSign is the first production consumer. Its workflow is useful as a reference implementation, but consumers should adopt the shared actions/configuration model rather than copy LibreSign-specific package rules.
