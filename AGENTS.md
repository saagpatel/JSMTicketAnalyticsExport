# JSMTicketAnalyticsExport Codex Playbook

## Communication Contract

Follow the global Codex communication contract. Keep updates short, PM-readable, operator-grade, and focused on what changed, what passed, and what still needs attention.

## Project Goal

JSMTicketAnalyticsExport is a local Python CLI that exports Jira Service Management tickets from a configured Jira Cloud instance, bypasses the native export cap through paginated REST calls, and writes canonical CSV, JSON, and manifest outputs for analytics under the configured output directory.

## First Read

- `README.md`
- `CLAUDE.md`
- `IMPLEMENTATION-ROADMAP.md`
- `requirements.txt`
- `.codex/verify.commands`

## Core Rules

- Never store Jira API tokens in source, config, `.env`, shell history, or generated artifacts; use macOS Keychain through `keyring`.
- Route HTTP calls through the existing retry/backoff wrapper; do not add raw Jira API calls.
- Resolve Jira field IDs dynamically from field metadata on each run; do not hardcode custom field IDs.
- Keep export outputs under `~/Analytics/JSM/`, not inside the repo.
- Every export run must produce `manifest.json` alongside the CSV and JSON data.
- Do not run live exports or hit the real Jira API unless the operator explicitly asks for that action.

## Codex App Usage

- Use Codex App Projects for repo-scoped implementation, tests, and local exporter maintenance.
- Use Worktrees for auth handling, Jira API pagination, schema normalization, manifest contract, launchd scheduling, or broad output-format changes.
- Use file search before editing because field mapping, output writing, retry behavior, and manifest generation are tightly coupled.
- Use artifacts for reusable analytics notes, sample schema handoffs, or operator-facing export summaries.
- Treat connector access and Jira credentials as task-gated; local tests are the default verification path.

## Verification

Use `.codex/verify.commands` as the canonical local gate. Current session note: local unit tests passed without requiring live Jira credentials.

## Done Criteria

- The relevant verifier commands have been run, or the exact blocker is recorded.
- Export-contract changes include unit tests for CSV, JSON, and manifest behavior.
- Any live Jira/API action was explicitly requested and its output path was verified.
