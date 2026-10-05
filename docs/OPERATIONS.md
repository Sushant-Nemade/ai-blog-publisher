# Operations and Release Boundaries

## Secrets and Data

Keep `.env`, private drafts and provider credentials out of Git and Pages artifacts. Only `blogboard/web` is deployed. Generation sends topics, context and content to configured providers; do not submit private, personal or proprietary material without permission and appropriate provider/data-processing review.

Opik/Sentry integrations are not required by the release and no telemetry is configured by default. Existing optional remote prompt behavior requires a separately configured Opik library/account; do not enable it without reviewing prompt disclosure and costs.

## Publication Recovery

Publication takes an exclusive `.publish.lock`. If a process crashes, inspect for a surviving publisher before manually removing a stale lock. Never remove a lock while a writer is active. Single-file replacements are atomic; the entire multi-file write is not a filesystem transaction.

An article is stored before its index is promoted. Failed index promotion can leave an orphan article, but not a newly broken published link. Retry the same reviewed digest after resolving the failure. The content-addressed path makes the operation idempotent. Keep backups of committed indexes and article files.

Corrupt JSON, denied storage access and missing article files fail publication. Investigate and restore the last valid index; do not replace a corrupt registry with an empty list merely to continue.

## Deploy and Roll Back

Pages deployment runs only after the CI workflow passes for a main-branch push. It checks out that tested revision, builds the pinned browser assets, verifies article indexes, and uploads only the static site. Deployment concurrency is serialized; drafts and secrets are never uploaded.

To roll back, restore the prior known-good reviewed content in a new change and rerun CI/deployment. Never force-push or delete upstream history. Check the live article and category links after delivery. GitHub Pages has platform limitations and no application-specific SLA is promised.

## Live Verification Checklist

1. Configure a provider key locally or through an approved secret store; do not send it through chat.
2. Generate one bounded tutorial draft and verify a clean failure path for unavailable providers.
3. Inspect content, sources, title, category and date; verify factual and licensing claims.
4. Inspect its digest, publish explicitly, and verify all index references.
5. Deploy reviewed content and inspect the actual live article on desktop and mobile.
6. Record model/provider, date, sanitized result and remaining limits without recording credentials or private prompts.

Repeat separately for opt-in news research and R2 history. Offline fixture success does not satisfy these live checks.