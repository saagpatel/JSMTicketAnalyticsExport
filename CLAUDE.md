# JSM Ticket Analytics Export

## Overview
Python CLI script that exports all JSM tickets from servicedesk.inside-box.net via the Jira REST API, bypassing the native 1,000-row export cap. Produces canonical CSV + JSON datasets for downstream IT analytics — monthly metrics, quarterly leadership briefs, and division-level breakdowns.

## Tech Stack
- **Python**: 3.11+
- **Auth**: Jira REST API v3 + API token via `keyring` (macOS Keychain — never plaintext)
- **HTTP**: `requests` 2.31+
- **Output**: stdlib `csv` + `json`
- **Scheduling**: macOS `launchd` via `.plist` in `~/Library/LaunchAgents`
- **Instance**: `servicedesk.inside-box.net` · Project key: `IT`

## Development Conventions
- Type annotations on all functions (Python 3.11 style — `list[str]`, `dict[str, Any]`)
- Single-responsibility functions — each function does one thing, testable in isolation
- All API calls wrapped in retry logic with exponential backoff
- Secrets retrieved via `keyring.get_password()` — never via env vars or config files
- File naming: `snake_case.py` throughout
- Log to stdout with timestamps via `logging` module (INFO default, DEBUG via `--verbose`)

## Current Phase
**Phase 0: Foundation + Core Export**
See IMPLEMENTATION-ROADMAP.md for full phase details.

## Key Decisions
| Decision | Choice | Why |
|----------|--------|-----|
| Credential storage | macOS Keychain via `keyring` | Never in plaintext, works with cron/launchd |
| Pagination strategy | `startAt` cursor (JQL-based) | JSM REST v3 standard — no token cursor available |
| Field ID resolution | Dynamic from `/rest/api/3/field` on each run | Resilient to JSM schema changes |
| Output schema | Flat CSV row — one ticket per row | Drop directly into Excel/Sheets, no transform needed |
| Scheduling | macOS `launchd` plist | More reliable than cron on macOS, survives sleep/wake |
| Rate limiting | Token bucket at 8 req/s (buffer below 10 req/s cap) | Avoids 429s during large backfills |

## Do NOT
- Do not hardcode `customfield_10102` or `customfield_10113` — always resolve field IDs dynamically from the field metadata endpoint
- Do not store the API token in `.env`, config files, or source code — use `keyring` only
- Do not make raw API calls without retry + backoff — all HTTP calls go through the `api_get()` wrapper
- Do not add features not in the current phase of IMPLEMENTATION-ROADMAP.md
- Do not write output files to the project directory — always write to `~/Analytics/JSM/`
- Do not skip the manifest file — every export run must produce a `manifest.json` alongside the data files
