<!--
SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Downstream patches

This directory contains explicit patches applied to imported upstream workflows.

Each rendered template is declared in `upstream/templates.json` with:

- an immutable vendored source under `upstream/vendor/`;
- zero or more ordered unified-diff patches from this directory;
- a generated destination under GitHub's native `workflow-templates/` directory.

Render all declared templates with:

```bash
python3 scripts/render_upstream.py sync upstream/templates.json
```

CI runs the corresponding `check` command and fails when a committed generated
template does not match its vendored source plus patches.

Patches should stay minimal. Product-specific behavior belongs in consumer
configuration unless the difference is required by the shared downstream
workflow contract.
