<!--
SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# First merged contribution workflow

The `first-merged-contribution` workflow template thanks a contributor after the
first pull request they actually get merged in a repository.

It is designed for `pull_request_target` and intentionally does not check out,
download, or execute pull-request content. The workflow only reads event
metadata, checks the contributor's merged pull-request history, and creates a
comment on the merged pull request. The comment carries an internal marker so
reruns are idempotent and do not create duplicate thank-you messages.

## Repository variables

All variables are optional:

- `FIRST_MERGED_CONTRIBUTION_MESSAGE`: complete custom message template.
  Supported placeholders are `{user}`, `{repository}`, `{pull_request}`,
  `{survey_url}`, and `{community_url}`.
- `CONTRIBUTOR_SURVEY_URL`: survey base URL. The workflow appends
  `source=github-first-merged-pr` and the repository name.
- `COMMUNITY_URL`: optional community link.

When `FIRST_MERGED_CONTRIBUTION_MESSAGE` is unset, the workflow uses a short
generic thank-you message and appends the optional survey and community links.

## Manual retry

The workflow also supports `workflow_dispatch` with a required
`pull_request_number` input. This is intended for recovering from a failed
post-merge run or validating the installation against an already merged first
contribution. The same first-merge check and duplicate-comment guard are applied
before a comment can be created.

## Permissions and security

The workflow starts with `permissions: {}` and grants only:

- `contents: read`;
- `pull-requests: write`.

The write permission is required only to create the pull-request comment.

The implementation uses the GitHub-maintained `actions/github-script` action
pinned to an immutable commit. It does not use a Docker action or build a
container image, so it does not inherit the obsolete Debian/Node container used
by the previous third-party first-interaction action.

Because the workflow runs as `pull_request_target`, never add checkout or any
execution of code, scripts, artifacts, or configuration from the pull request
head to this workflow.
