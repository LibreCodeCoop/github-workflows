<!--
SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Cross-repository automation

LibreCode cross-repository workflow automation is authenticated through the
**LibreCode Workflow Automation** GitHub App.

## Installation

The App is installed on the `LibreCodeCoop` organization with access to all
repositories.

The installation-level access is intentionally broad so newly created LibreCode
repositories do not require a manual App reconfiguration before they can be
onboarded.

Actual automation remains opt-in:

- catalog publication targets only `LibreCodeCoop/.github`;
- consumer synchronization targets only repositories declared in
  `consumers.json`;
- catalog entries are limited by `workflow-catalog.json`.

## GitHub App permissions

Repository permissions:

- Contents: read/write;
- Pull requests: read/write;
- Workflows: read/write;
- Metadata: read.

No organization administration, members, secrets or repository administration
permissions are required.

## Repository configuration

`LibreCodeCoop/github-workflows` stores:

- Actions variable `LIBRECODE_WORKFLOW_APP_ID`;
- Actions secret `LIBRECODE_WORKFLOW_APP_PRIVATE_KEY`.

The private key must never be committed to the repository.

## Token model

Workflows do not store a long-lived installation token.

Each write-capable job uses `actions/create-github-app-token`, pinned to a
full commit SHA, to create a short-lived installation token.

Although the App is installed across the organization, each generated token is
further restricted to the exact destination repository:

- catalog publisher: `.github`;
- consumer sync: the current consumer repository from the matrix.

The token also requests only the permissions needed for the operation.

## Onboarding a repository

A new repository does not require reinstalling or reconfiguring the App.

To opt a repository into managed workflow synchronization:

1. validate the desired workflows in that repository;
2. add the repository and workflow names to `consumers.json`;
3. merge the reviewed change;
4. review the automatically created adoption PR;
5. merge the lock file;
6. confirm a subsequent synchronization is a no-op.

## Publishing a template

A generated file under `workflow-templates/` is not automatically public.

Add the template name to `workflow-catalog.json` only after the workflow has
completed its security and consumer validation.

This prevents release, credential-sensitive or experimental workflows from
appearing in **Actions -> New workflow** prematurely.

## Private-key rotation

Rotate the App private key when:

- compromise is suspected;
- an administrator with access to the key leaves the responsible team;
- organizational security policy requires rotation.

Rotation procedure:

1. generate a new private key in the GitHub App settings;
2. replace `LIBRECODE_WORKFLOW_APP_PRIVATE_KEY` in the repository Actions
   secrets;
3. run/observe catalog publication and consumer synchronization successfully;
4. delete the old private key from the GitHub App settings.

Do not delete the old key before the new key has been validated.

## Validation

The initial production validation confirmed:

- GitHub App configuration can be read by Actions;
- scoped installation tokens can be created;
- the catalog repository can be checked out and updated;
- a catalog no-op does not leave an update PR open;
- `LibreCodeCoop/extract` can be checked out and updated;
- managed workflows can be adopted into the lock file;
- a subsequent synchronization with current hashes creates no PR.


## Portable consumer authentication

The installed workflow updater does not infer authentication from the consumer's
organization name. Consumers select an explicit repository variable:

\`WORKFLOW_SYNC_AUTH_MODE\`

Supported values:

- \`librecode-app\` — default for existing LibreCode-managed repositories. Uses
  \`LIBRECODE_WORKFLOW_APP_ID\` and \`LIBRECODE_WORKFLOW_APP_PRIVATE_KEY\`.
- \`github-app\` — uses a consumer-owned GitHub App configured through
  \`WORKFLOW_SYNC_APP_ID\` and \`WORKFLOW_SYNC_APP_PRIVATE_KEY\`.
- \`token\` — uses a consumer-owned repository-scoped credential stored as
  \`WORKFLOW_SYNC_TOKEN\`.
- \`github-token\` — uses the workflow's built-in \`GITHUB_TOKEN\`.

A consumer-owned GitHub App is preferred for independent projects because it
keeps credentials under the consumer's control while still allowing generated
pull requests to trigger normal repository automation.

The \`github-token\` mode is intentionally explicit. GitHub suppresses workflow
runs caused by most events created with the repository \`GITHUB_TOKEN\`, which
means a pull request created through that mode may not trigger the consumer's
normal pull-request CI. Use it only when that limitation is acceptable or when
another mechanism explicitly triggers validation.

For GitHub App credentials, request only the repository permissions needed by
the updater: Contents write, Pull requests write and Workflows write. Do not
install or share the LibreCode GitHub App/private key with external consumers.
