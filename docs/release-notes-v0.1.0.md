# jsm-ticket-analytics-export v0.1.0 — initial release

> **Jira's 1,000-row export cap, ignored.**

First public release. A CLI that exports **every** Jira Service Management ticket
through the REST API — not the first 1,000 — into clean CSV + JSON datasets plus
an audit manifest.

## Install

```bash
pip install jsm-ticket-analytics-export
```

## Highlights

- **Unlimited export** — paginates the REST API past the native 1,000-row cap
- **CSV + JSON** output, ready for Excel/Sheets or a data pipeline
- **Audit manifest** per run — row counts, resolved field IDs, exact JQL, timing
- **Backfill** mode auto-splits full history into per-month files
- **Secure credentials** in the OS keychain via `keyring` — never plaintext
- **Configurable** via `JSM_JIRA_INSTANCE` / `JSM_PROJECT_KEY`
- Console commands: `jsm-export` and `jsm-export-setup`

## Quick start

```bash
export JSM_JIRA_INSTANCE="https://your-org.atlassian.net"
export JSM_PROJECT_KEY="SUPPORT"
jsm-export-setup     # store your Jira email + API token (one time)
jsm-export           # export last month → ~/Analytics/JSM/
```

Requires Python 3.11+. Full usage in the [README](../README.md); details in
[CHANGELOG.md](../CHANGELOG.md).
