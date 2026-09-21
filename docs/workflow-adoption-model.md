<!--
SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Workflow adoption model

Use this guide when adding or migrating automation into `LibreCodeCoop/github-workflows`.

## Default preference

Prefer the option that centralizes implementation without hiding repository-specific behavior.

The decision order is:

1. reusable workflow;
2. composite action;
3. installed organization workflow template.

A copied template is not the default merely because an upstream project publishes one.

## Reusable workflow

Prefer a reusable workflow when the whole job or workflow can be expressed behind a stable caller contract.

Good fit:

- CI orchestration shared by many repositories;
- release or validation flows with well-defined inputs and secrets;
- behavior that should receive fixes centrally without copying implementation;
- permissions and secrets can be declared clearly at the caller boundary.

Avoid when:

- the repository must own event-specific structure that cannot be expressed cleanly by the caller;
- callers need to change internal jobs/steps rather than inputs;
- GitHub reusable-workflow limitations prevent required nesting, secrets or environment behavior.

A caller should remain intentionally small.

## Composite action

Prefer a composite action when the reusable unit is a sequence of steps inside a job rather than the workflow itself.

Good fit:

- setup;
- validation helpers;
- deterministic transformations;
- repeated command sequences with a stable input/output contract.

Keep non-trivial parsing and business rules in tested code invoked by the action rather than large shell blocks.

## Organization workflow template

Use an installed template when the consumer repository genuinely needs to own the workflow file.

Good fit:

- event declarations belong to the repository;
- repository-level customization is expected;
- GitHub cannot express the needed abstraction as a reusable workflow;
- developers benefit from discovering/installing the workflow through **Actions -> New workflow**.

A managed template must have:

- organization catalog metadata;
- provenance;
- deterministic generation when derived from upstream;
- explicit LibreCode patches;
- a consumer update path;
- divergence protection when centrally synchronized.

## Upstream-derived workflows

Do not automatically mirror an upstream template as a LibreCode template.

For every upstream workflow, review:

1. whether the implementation should instead become a reusable workflow;
2. runner labels;
3. owner/organization checks;
4. permissions;
5. credentials and environments;
6. third-party actions;
7. assumptions about repository layout;
8. local patch requirements;
9. license and branding assets.

Shared LibreCode behavior belongs in `github-workflows`, not in repeated consumer-local patches.

## Versioning

Reusable workflows and actions are code dependencies and should be referenced through a deliberate versioning policy.

Installed templates are copied artifacts. Their source revision is tracked centrally, while consumers are updated through reviewable synchronization PRs.

Do not mix these models implicitly.

## Review checklist

Before accepting a new shared workflow:

- Can the implementation be centralized as a reusable workflow?
- If not, is a composite action the reusable unit?
- If a template is required, why must the workflow file remain consumer-owned?
- Is repository-specific variability represented as explicit inputs/configuration rather than forks?
- Are substantial scripts extracted into tested code?
- Are permissions least-privilege?
- Are third-party actions pinned according to project policy?
- Does the consumer have a documented update and divergence path?

## Consumer lock provenance

Materialized workflow consumers use `.github/actions-lock.txt` as a management
and provenance record.

New lock entries use SHA-256 and record:

- the installed workflow filename;
- the catalog workflow digest;
- the released `github-workflows` platform version;
- the immutable `github-workflows` source commit used by the updater;
- the exact `LibreCodeCoop/.github` catalog commit checked out by the run.

Legacy two-column MD5 locks remain readable. The next successful synchronization
migrates them deterministically to the provenance format without rewriting a
workflow when its effective bytes are unchanged.

The consumer-local `<workflow>.patch` remains authoritative for deliberate
local differences, and unexplained divergence continues to fail closed.
