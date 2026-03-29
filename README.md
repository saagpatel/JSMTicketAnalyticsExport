![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey)

# JSM Ticket Analytics Export

A Python CLI that exports Jira Service Management tickets via the REST API, bypassing the native 1,000-row export cap. Produces per-month CSV and JSON datasets plus audit manifests — designed for recurring IT analytics pipelines.

Credentials are stored in macOS Keychain (never in plaintext), the API client is rate-limited and retry-wrapped, and the backfill mode splits a full export into per-month files automatically.

---

## Screenshot

![Terminal output placeholder](docs/screenshot.png)

*Example terminal output from a monthly export run.*

---

## Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| HTTP | `requests` (raw REST, no PyGithub/PyJira) |
| Credentials | `keyring` — macOS Keychain only |
| Output formats | CSV, JSON |
| Scheduling | macOS `launchd` (plist included) |

---

## Prerequisites

- Python 3.11 or later
- macOS (credential storage relies on Keychain via `keyring`)
- A Jira Cloud instance with a project you have read access to
- An [Atlassian API token](https://id.atlassian.com/manage-profile/security/api-tokens)

---

## Getting Started

**1. Install dependencies**

```bash
pip install -r requirements.txt
```

**2. Store credentials**

Credentials are persisted to macOS Keychain — never written to disk in plaintext.

```bash
python setup_keychain.py
```

Enter your Atlassian account email and API token when prompted. The script validates both against the live Jira API before saving.

**3. Run an export**

```bash
# Export a specific month
python jsm_export.py --month 2026-02

# Export everything from a date onward
python jsm_export.py --since 2026-01-15

# Full historical backfill (all tickets, split by month)
python jsm_export.py --backfill

# Count tickets without writing files
python jsm_export.py --dry-run --month 2026-02

# Enable DEBUG logging
python jsm_export.py --month 2026-02 --verbose
```

Output writes to `~/Analytics/JSM/` by default (see `config.py`).

---

## Output Files

| File | Description |
|---|---|
| `YYYY-MM.csv` | Flat ticket rows for one calendar month |
| `YYYY-MM.json` | Same rows as structured JSON |
| `YYYY-MM-manifest.json` | Audit trail: row count, JQL used, custom field mappings, timing, any transform errors |
| `all-time.json` | Cumulative dataset appended after every run |

Each `TicketRow` includes: ticket ID, summary, URL, issue type, priority, labels, components, status, resolution, resolution time, assignee, reporter, division, manager, SLA breach flag, SLA time-to-resolution, and all key timestamps.

---

## Scheduling

The included `com.saagar.jsm-export.plist` runs the export on the 1st of each month at 06:00 via `launchd`.

```bash
mkdir -p ~/Analytics/JSM/logs
cp com.saagar.jsm-export.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.saagar.jsm-export.plist

# Verify
launchctl list | grep jsm

# Unload
launchctl unload ~/Library/LaunchAgents/com.saagar.jsm-export.plist
```

Logs write to `~/Analytics/JSM/logs/`.

---

## Project Structure

```
JSMTicketAnalyticsExport/
├── jsm_export.py          # CLI entrypoint and pipeline orchestration
├── jira_client.py         # Authenticated, rate-limited REST client
├── field_resolver.py      # Resolves custom field names to Jira field IDs
├── transformer.py         # Maps raw Jira issue dicts to TicketRow
├── writer.py              # CSV, JSON, and manifest file writers
├── all_time_appender.py   # Appends new rows to the cumulative dataset
├── models.py              # TicketRow, ExportManifest, FieldMapping dataclasses
├── config.py              # Non-secret configuration constants
├── setup_keychain.py      # One-time interactive credential setup
├── com.saagar.jsm-export.plist  # launchd schedule (monthly)
├── requirements.txt
└── tests/
```

---

## Configuration

Non-secret constants live in `config.py`: Jira instance URL, project key, output directory, rate limit (8 req/s), retry count, and keyring service name. No environment variables required — all secrets stay in macOS Keychain.

---

## License

MIT — see [LICENSE](LICENSE).
