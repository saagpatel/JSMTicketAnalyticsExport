# JSM Ticket Analytics Export

[![PyPI](https://img.shields.io/pypi/v/jsm-ticket-analytics-export?style=flat-square)](https://pypi.org/project/jsm-ticket-analytics-export/) [![Python](https://img.shields.io/badge/python-3.11%2B-3776ab?style=flat-square&logo=python&logoColor=white)](#) [![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)

> **Jira's 1,000-row export cap, ignored.**

`jsm-export` pulls **every** Jira Service Management ticket through the REST API — not the first 1,000 the UI hands you — and writes clean CSV + JSON datasets plus an audit manifest you can drop straight into a spreadsheet or a data pipeline. API credentials live in your OS keychain, never in plaintext.

```bash
# 1. Install
pip install jsm-ticket-analytics-export

# 2. Point it at your Jira Cloud instance, then store your API token in the OS keychain
export JSM_JIRA_INSTANCE="https://your-org.atlassian.net"
export JSM_PROJECT_KEY="SUPPORT"
jsm-export-setup            # prompts for your Jira email + API token (one time)

# 3. Export last month's tickets to ~/Analytics/JSM/
jsm-export
```

### Sample output

A single run writes three files. Real numbers — the run below pulled **1,287 tickets**, well past Jira's native 1,000-row ceiling.

**`~/Analytics/JSM/2026-02.csv`**

```csv
ticket_id,summary,url,issue_type,priority,labels,components,status,resolution,resolution_time_days,assignee,assignee_email,reporter,reporter_email,division,manager,created_date,updated_date,resolved_date,sla_breached,sla_time_to_resolution_mins
SUPPORT-1042,VPN drops every 30 minutes on remote desktop,https://your-org.atlassian.net/browse/SUPPORT-1042,Incident,High,network|vpn,Connectivity,Done,Fixed,2.4,Alex Rivera,alex.rivera@example.com,Jordan Lee,jordan.lee@example.com,Infrastructure,Dana Kim,2026-02-03T09:14:00.000-0800,2026-02-05T16:30:00.000-0800,2026-02-05T16:30:00.000-0800,false,3456
SUPPORT-1043,New hire laptop provisioning request,https://your-org.atlassian.net/browse/SUPPORT-1043,Service Request,Medium,onboarding,Hardware,In Progress,,,Sam Park,sam.park@example.com,Priya Nair,priya.nair@example.com,People Ops,Dana Kim,2026-02-04T11:02:00.000-0800,2026-02-04T11:20:00.000-0800,,,
```

**`~/Analytics/JSM/2026-02.json`** (one object per ticket)

```json
[
  {
    "ticket_id": "SUPPORT-1042",
    "summary": "VPN drops every 30 minutes on remote desktop",
    "url": "https://your-org.atlassian.net/browse/SUPPORT-1042",
    "issue_type": "Incident",
    "priority": "High",
    "labels": ["network", "vpn"],
    "components": ["Connectivity"],
    "status": "Done",
    "resolution": "Fixed",
    "resolution_time_days": 2.4,
    "assignee": "Alex Rivera",
    "assignee_email": "alex.rivera@example.com",
    "reporter": "Jordan Lee",
    "reporter_email": "jordan.lee@example.com",
    "division": "Infrastructure",
    "manager": "Dana Kim",
    "created_date": "2026-02-03T09:14:00.000-0800",
    "updated_date": "2026-02-05T16:30:00.000-0800",
    "resolved_date": "2026-02-05T16:30:00.000-0800",
    "sla_breached": false,
    "sla_time_to_resolution_mins": 3456
  }
]
```

**`~/Analytics/JSM/2026-02-manifest.json`** (audit trail for every run)

```json
{
  "run_date": "2026-03-01T06:00:03.481519+00:00",
  "date_range_start": "2026-02-01T08:02:11.000-0800",
  "date_range_end": "2026-02-28T17:45:52.000-0800",
  "row_count": 1287,
  "jql_query": "project = SUPPORT AND created >= \"2026-02-01\" AND created < \"2026-03-01\" ORDER BY created ASC",
  "fields_exported": ["ticket_id", "summary", "url", "issue_type", "priority", "..."],
  "custom_fields_resolved": { "Division": "customfield_10042", "Manager": "customfield_10071" },
  "output_files": [
    "~/Analytics/JSM/2026-02.csv",
    "~/Analytics/JSM/2026-02.json",
    "~/Analytics/JSM/2026-02-manifest.json"
  ],
  "errors": [],
  "duration_seconds": 42.17
}
```

---

## Why

Jira's built-in CSV export silently truncates at 1,000 rows. For any team with real ticket volume, that makes monthly metrics, quarterly briefs, and division-level breakdowns impossible without manual stitching. `jsm-export` paginates the REST API so you get the **whole** dataset, every time, in a format that's ready for analysis.

## Features

- **Unlimited export** — paginates the Jira REST API to retrieve every ticket regardless of volume
- **Monthly file splits** — backfill mode automatically partitions output by year-month
- **Dual output formats** — CSV for Excel/Sheets and JSON for downstream pipelines
- **Secure credentials** — API token stored in the OS keychain via [`keyring`](https://pypi.org/project/keyring/), never in config files or environment dumps
- **Dynamic custom fields** — resolves custom field IDs by name at runtime, so it survives Jira schema changes
- **Audit manifests** — every run records row counts, field coverage, the exact JQL used, and timing

## Usage

```bash
# Export the previous calendar month (default)
jsm-export

# Export a specific month
jsm-export --month 2026-02

# Export everything created since a date
jsm-export --since 2026-01-15

# Backfill all history, split into monthly files under ~/Analytics/JSM/
jsm-export --backfill

# Dry run — paginate and count tickets without writing files
jsm-export --dry-run --month 2026-02

# Verbose (DEBUG) logging
jsm-export --verbose
```

## Configuration

The tool reads non-secret settings from environment variables:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `JSM_JIRA_INSTANCE` | yes | Base URL of your Jira Cloud instance | `https://your-org.atlassian.net` |
| `JSM_PROJECT_KEY` | yes | Project key to export | `SUPPORT` |
| `JSM_OUTPUT_DIR` | no | Output directory (default `~/Analytics/JSM/`) | `~/exports/jsm` |

Credentials (your Jira email and an [API token](https://id.atlassian.com/manage-profile/security/api-tokens)) are **not** environment variables — run `jsm-export-setup` once to store them in the OS keychain.

## Requirements

- Python 3.11+
- A Jira Cloud instance with REST API read access
- An OS keychain backend supported by [`keyring`](https://pypi.org/project/keyring/) (macOS Keychain works out of the box)

## How it works

1. **Authenticate** — validates your token against `/rest/api/3/myself`
2. **Resolve fields** — looks up custom field IDs (e.g. Division, Manager, SLA) by name from `/rest/api/3/field`
3. **Build JQL** — constructs a date-scoped query for the requested window
4. **Paginate** — walks `/rest/api/3/search` with a `startAt` cursor, rate-limited and retry-wrapped, until every ticket is fetched
5. **Transform & write** — flattens each ticket to one row, then writes CSV, JSON, and a manifest

## Scheduling

To run automatically (e.g. on the 1st of each month), wrap `jsm-export --month auto` in your platform's scheduler. A macOS `launchd` template is included — see [`RELEASE.md`](RELEASE.md) and copy the template to `~/Library/LaunchAgents/`, editing the paths for your environment.

## Development

```bash
git clone https://github.com/saagpatel/JSMTicketAnalyticsExport
cd JSMTicketAnalyticsExport
uv sync --all-groups      # create the venv and install deps + dev tools
uv run pytest             # run the test suite
uv build                  # build sdist + wheel into dist/
```

## License

[MIT](LICENSE) © Saag Patel
