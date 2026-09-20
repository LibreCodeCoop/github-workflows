<!--
SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Workflow family decisions

This document records the migration outcome for the workflow families evaluated in the
shared-workflow roadmap. Completion does not mean every upstream workflow is copied;
an explicit decision to keep a workflow local is a valid outcome when its behavior is
consumer-specific or credential-sensitive.

| Family | Decision | Status |
| --- | --- | --- |
| REUSE | Organization template | Cataloged and validated in consumers |
| info.xml lint | Organization template | Cataloged and validated |
| PHP lint / coding standards | Organization templates | Cataloged and validated |
| Psalm static analysis | Organization template | Cataloged and validated |
| ESLint / Stylelint / TypeScript | Organization templates | Cataloged; TypeScript validated in LibreSign |
| Node tests | Organization template | Cataloged and validated in LibreSign |
| Frontend build | `npm-build.yml` organization template | Cataloged and validated |
| Conventional Commits | Organization template | Cataloged and validated |
| OpenAPI | Organization template | Cataloged and validated |
| PHPUnit database workflows | Keep consumer-local for now | LibreSign copies materially diverge from current upstream through app-specific system packages, submodules and coverage behavior; centralizing them would create large product-specific patches |
| Dependency approval / auto-merge | Keep local until policy-compatible | Governed by `docs/dependency-update-policy.md` |
| npm audit remediation | Keep local | Credential and merge policy are repository-specific |
| App Store build/publish | Organization template available | Cataloged; installation remains opt-in because credentials and release policy are consumer-owned |
| Other release automation | Keep consumer-local unless generic | Requires an explicit credential and release contract before cataloging |

## Decision rule

A workflow is promoted to the organization catalog when its upstream behavior can be
preserved with small organization-level adaptations and at least one consumer can use it
without product-specific logic.

A workflow stays local when centralization would require substantial patches for one
product, personal/bot PAT assumptions, or product-specific release semantics.

These decisions should be revisited when upstream or consumer requirements materially
change; they are not an instruction to force all future workflows into either model.
