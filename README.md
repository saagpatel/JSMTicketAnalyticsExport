# JSM Ticket Analytics Export

Python CLI that exports all Jira Service Management tickets from your JSM instance via the REST API, bypassing the native 1,000-row export cap. Produces CSV + JSON datasets for IT analytics.

## Setup

### Requirements

- Python 3.11+
- macOS (uses Keychain for credential storage)

### Install

```bash
cd JSMTicketAnalyticsExport
pip install -r requirements.txt
```

### Store Credentials

Credentials are stored in macOS Keychain — never in plaintext files.

```bash
python setup_keychain.py
```

Enter your Atlassian email and API token when prompted. The script validates credentials against the Jira API before saving.

To generate an API token: [Atlassian API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens)

## Usage

### Export a specific month

```bash
python jsm_export.py --month 2026-02
```

Writes to `~/Analytics/JSM/`:
- `2026-02.csv` — flat ticket data
- `2026-02.json` — same data as JSON
- `2026-02-manifest.json` — audit trail (row count, JQL, duration, errors)

### Export from a date forward

```bash
python jsm_export.py --since 2026-01-15
```

### Full historical backfill

```bash
python jsm_export.py --backfill
```

Fetches all tickets ever created, splits output into per-month CSV/JSON files, and builds the cumulative `all-time.json`.

### Dry run (count only)

```bash
python jsm_export.py --dry-run --month 2026-02
```

Paginates and counts tickets without writing files.

### Verbose logging

```bash
python jsm_export.py --month 2026-02 --verbose
```

## Scheduling (launchd)

The included plist runs the export on the 1st of each month at 06:00.

```bash
# Create log directory
mkdir -p ~/Analytics/JSM/logs

# Install the launch agent
cp com.saagar.jsm-export.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.saagar.jsm-export.plist

# Verify it's loaded
launchctl list | grep jsm

# Manual test run
launchctl start com.saagar.jsm-export
```

Logs write to `~/Analytics/JSM/logs/`.

To unload: `launchctl unload ~/Library/LaunchAgents/com.saagar.jsm-export.plist`

## Output

All files write to `~/Analytics/JSM/`. The export never writes to the project directory.

| File | Description |
|------|-------------|
| `YYYY-MM.csv` | Flat ticket data for one month |
| `YYYY-MM.json` | Same data as JSON |
| `YYYY-MM-manifest.json` | Audit metadata (row count, JQL, timing) |
| `all-time.json` | Cumulative dataset, deduplicated by ticket ID |

## Configuration

Non-secret config lives in `config.py`:
- Instance URL, project key, output directory
- Rate limit (8 req/s), retry settings
- Keyring service name

Credentials are in macOS Keychain under the `jsm-analytics` service. Re-run `setup_keychain.py` to update them.
