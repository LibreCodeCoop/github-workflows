<!--
SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Nextcloud release automation

The public `Prepare release` workflow is the maintainer entry point for the
reusable release platform.

Normal releases have two human gates:

1. review and merge the generated release preparation pull request;
2. review and publish the generated GitHub Release draft.

Planning, finalization, milestone transition and post-publication verification
are automated around those gates.

## Consumer contract

A consumer repository provides a versioned `.nextcloud-release.yml` file and
installs `workflow-templates/prepare-release.yml`.

The manual entry point requires only the release branch. Optional inputs allow:

- an exact planning ref;
- an explicit version;
- alpha, beta, rc or final channel;
- an explicit open-backport override;
- follow-up milestone creation;
- normal or security mode;
- explicitly public-safe text for security mode.

The workflow delegates release policy to the pinned PHP release tool. GitHub
Actions owns orchestration, authentication, permissions and artifact handoff;
it does not reimplement version, changelog or milestone policy in YAML.

## Lifecycle

```text
Actions -> Prepare release
        -> ReleasePlan v1
        -> generated release PR
        -> maintainer review + merge
        -> PreparedRelease v1
        -> milestone transition
        -> GitHub Release draft
        -> maintainer review + Publish
        -> existing package/sign/App Store publisher
        -> PublicationVerification v1
```

The generated release PR is recognized by deterministic release-tool identity
and provenance. Post-merge continuation validates the actual merger permission
before any privileged release mutation.

## Authentication and permissions

Read-only planning uses the repository token with read permissions.

Mutating preparation/finalization stages use short-lived GitHub App installation
tokens scoped to the current repository. Consumers configure:

- `LIBRECODE_WORKFLOW_APP_ID` as an Actions variable;
- `LIBRECODE_WORKFLOW_APP_PRIVATE_KEY` as an Actions secret.

The reusable actions request only the permissions needed by each stage. The
whole workflow does not receive broad write permissions.

## Release tool pinning

The reusable actions install an exact released `release-tool` PHAR, verify its
published SHA-256 checksum and expose the same CLI used for local diagnostics and
recovery. No production path executes a floating `latest` artifact.

## Publication

Publishing the GitHub Release remains an explicit maintainer action.

The existing consumer-specific publisher remains responsible for packaging,
signing, uploading the release asset and App Store publication. After the
release event, the workflow restores the finalized release contracts and
produces `PublicationVerification v1` only when the published release identity,
asset, publisher handoff and App Store visibility agree.

## Recovery and local parity

Every stage contract can be reproduced with the release-tool CLI for dry-run,
diagnostics and manual recovery. The public LibreSign documentation contains the
consumer-facing procedure and recovery guidance; this repository documents the
reusable orchestration contract only.

The previous `release-nextcloud-app` template is retired from the public
catalog because it created a release directly and bypassed the final staged
contracts.
