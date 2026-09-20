<!--
SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Security policy

Please do not report suspected vulnerabilities in a public issue.

Use GitHub private vulnerability reporting when available. Otherwise contact
LibreCode Coop at **contact@librecode.coop**.

Do not publish credentials, tokens, private keys, customer data or exploit
details in public discussions.

Reusable workflows should follow these controls:

- pin third-party Actions to immutable commit SHAs;
- keep credentials in consumer-owned protected environments;
- use minimum GitHub token permissions;
- avoid privileged execution of untrusted pull request code;
- keep planning non-mutating by default;
- require explicit invocation for publication or other mutations.
