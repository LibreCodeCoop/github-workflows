<!--
SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# First merged PR comment

The `first-merged-pr-comment` action detects a contributor's first merged pull
request and creates one idempotent comment from a repository-defined template.

The action is intentionally generic. It has no concept of surveys, community
links, documentation URLs, labels, or any other product-specific destination.
The consumer composes the complete message, including arbitrary URLs and query
strings, from built-in placeholders.

## Action contract

Required inputs:

- `github-token`: token used for the GitHub API;
- `message-template`: complete Markdown message template.

Optional input:

- `pull-request-number`: used by manual retries. Event-driven executions read
  the pull request from the event payload.

Outputs:

- `is-first-merged`;
- `comment-created`;
- `contributor-login`;
- `pull-request-number`.

## Built-in placeholders

The message renderer exposes only GitHub-derived values:

- `{server_url}`
- `{api_url}`
- `{repository}`
- `{repository_owner}`
- `{repository_name}`
- `{repository_url}`
- `{pull_request_number}`
- `{pull_request_url}`
- `{contributor_login}`
- `{contributor_mention}`
- `{contributor_url}`
- `{merge_commit_sha}`

Any placeholder may use the `urlencode` filter when it must be embedded in a
URL component:

```text
https://example.org/form?repo={repository|urlencode}&pr={pull_request_number|urlencode}
```

The renderer performs textual substitution only. It does not evaluate shell,
Python, JavaScript, GitHub expressions, Jinja, Handlebars, or template
functions. Unknown placeholders and unknown filters fail the action instead of
publishing a partially rendered message.

## Repository configuration

The organization workflow template requires the repository Actions variable
`FIRST_MERGED_PR_MESSAGE`. The workflow passes that variable directly to the
action. If it is absent or empty, the action fails instead of publishing a
fallback message.

Configure the variable under **Settings → Secrets and variables → Actions →
Variables**. A consumer can put its entire Markdown message in that single
variable. For example:

```text
Thanks {contributor_mention}! Your first pull request to {repository_name} has been merged.

Repository: {repository_url}

Feedback: https://feedback.example/respond?repository={repository|urlencode}&contributor={contributor_login|urlencode}&pr={pull_request_number|urlencode}
```

The URLs above are examples only. The action does not know or assign meaning to
them.

## Retry and idempotency

The workflow template supports `workflow_dispatch` with a pull request number.
The action evaluates the contribution at the historical close time of that pull
request, so a retry remains valid even after the contributor has additional
merged pull requests.

Successful comments include an internal HTML marker. A retry against a pull
request that already received the message exits successfully without creating a
duplicate.

## Security model

The workflow uses `pull_request_target` because the comment requires write
permission after a pull request from a fork is merged. The privileged workflow
must therefore never execute untrusted pull-request content.

The provided template:

- starts from `permissions: {}`;
- grants only `pull-requests: write` to the job;
- does not check out repository or pull-request content;
- does not download or execute pull-request artifacts;
- calls the LibreCode composite action at an immutable commit;
- uses Python's standard library only;
- keeps the GitHub authorization header off redirected requests;
- only trusts the idempotency marker when it appears in a bot-authored comment;
- does not build or run a Docker image;
- does not install runtime dependencies.

Do not add checkout or execution of pull-request-head content to this workflow.


### pull_request_target policy

GitHub treats `pull_request_target` as a privileged event. Repositories or
organizations that restrict this event must explicitly allow this workflow.
The workflow is designed for that privileged model: it never checks out or
executes pull-request-head content and requests only the permission needed to
create the pull-request comment.
