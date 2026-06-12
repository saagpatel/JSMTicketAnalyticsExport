# JSM Ticket Analytics Export

Python CLI that exports all JSM tickets from `your-org.atlassian.net` via the Jira REST API, bypassing the native 1,000-row export cap. Produces CSV + JSON datasets for IT analytics — monthly metrics, quarterly briefs, and division-level breakdowns.

## Stack

- **Python**: 3.11+ · `requests` 2.31+ · stdlib `csv` + `json`
- **Auth**: Jira REST API v3 + API token via `keyring` (macOS Keychain)
- **Scheduling**: macOS `launchd` via `.plist` in `~/Library/LaunchAgents`
- **Instance**: `your-org.atlassian.net` · Project key: `IT`

## Conventions

- Type-annotate all functions (Python 3.11 style — `list[str]`, `dict[str, Any]`)
- Single-responsibility functions; each testable in isolation
- Route all HTTP calls through `api_get()` — includes retry + exponential backoff
- Retrieve secrets via `keyring.get_password()` — never env vars or config files
- File naming: `snake_case.py` throughout
- Log to stdout with timestamps via `logging` (INFO default, `--verbose` for DEBUG)
- Write output files to `~/Analytics/JSM/` — not the project directory
- Every export run must produce a `manifest.json` alongside the data files

## Key Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Credential storage | macOS Keychain via `keyring` | Never plaintext; works with cron/launchd |
| Pagination strategy | `startAt` cursor (JQL-based) | JSM REST v3 standard — no token cursor available |
| Field ID resolution | Dynamic from `/rest/api/3/field` on each run | Resilient to JSM schema changes |
| Output schema | Flat CSV row — one ticket per row | Drop directly into Excel/Sheets, no transform needed |
| Scheduling | macOS `launchd` plist | More reliable than cron on macOS, survives sleep/wake |
| Rate limiting | Token bucket at 8 req/s (buffer below 10 req/s cap) | Avoids 429s during large backfills |

## Gotchas

- Field IDs: always resolve `customfield_10102` and `customfield_10113` dynamically from the field metadata endpoint — never hardcode them
- Scope: stay within the current phase of IMPLEMENTATION-ROADMAP.md before adding features

<!-- portfolio-context:start -->
# Portfolio Context

## What This Project Is

Python CLI script that exports all JSM tickets from your-org.atlassian.net via the Jira REST API, bypassing the native 1,000-row export cap. Produces canonical CSV + JSON datasets for downstream IT analytics — monthly metrics, quarterly leadership briefs, and division-level breakdowns.

## Current State

**Phases 0–2 complete.** Core export (Phase 0), custom field resolution + SLA extraction + all-time append (Phase 1), and launchd scheduling + backfill mode (Phase 2) are all implemented. See IMPLEMENTATION-ROADMAP.md for phase details.

## Stack

- **Python**: 3.11+
- **Auth**: Jira REST API v3 + API token via `keyring` (macOS Keychain — never plaintext)
- **HTTP**: `requests` 2.31+
- **Output**: stdlib `csv` + `json`
- **Scheduling**: macOS `launchd` via `.plist` in `~/Library/LaunchAgents`
- **Instance**: `your-org.atlassian.net` · Project key: `IT`

## How To Run

- Type annotations on all functions (Python 3.11 style — `list[str]`, `dict[str, Any]`)
- Single-responsibility functions — each function does one thing, testable in isolation
- All API calls wrapped in retry logic with exponential backoff
- Secrets retrieved via `keyring.get_password()` — never via env vars or config files
- File naming: `snake_case.py` throughout
- Log to stdout with timestamps via `logging` module (INFO default, DEBUG via `--verbose`)

## Known Risks

- Do not hardcode `customfield_10102` or `customfield_10113` — always resolve field IDs dynamically from the field metadata endpoint
- Do not store the API token in `.env`, config files, or source code — use `keyring` only
- Do not make raw API calls without retry + backoff — all HTTP calls go through the `api_get()` wrapper
- Do not add features not in the current phase of IMPLEMENTATION-ROADMAP.md
- Do not write output files to the project directory — always write to `~/Analytics/JSM/`
- Do not skip the manifest file — every export run must produce a `manifest.json` alongside the data files

## Next Recommended Move

Use this context plus the README and supporting docs to resume the next active task, then promote the repo beyond minimum-viable by capturing a dedicated handoff, roadmap, or discovery artifact.

<!-- portfolio-context:end -->
