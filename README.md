# JSM Ticket Analytics Export

[![Python](https://img.shields.io/badge/python-%233776ab?style=flat-square&logo=python)](#) [![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](#)

> Jira's 1,000-row export cap is a lie — this CLI ignores it entirely.

A Python CLI that exports Jira Service Management tickets via the REST API, bypassing the native 1,000-row cap. Produces per-month CSV and JSON datasets plus audit manifests. Credentials live in macOS Keychain (never in plaintext), the API client is rate-limited and retry-wrapped, and backfill mode auto-splits a full export into monthly files.

## Features

- **Unlimited export** — paginates the Jira REST API to retrieve every ticket regardless of volume
- **Monthly file splits** — backfill mode automatically partitions output by year-month
- **Dual output formats** — CSV for Excel/Sheets analytics and JSON for downstream pipelines
- **Secure credentials** — API token stored in macOS Keychain via `keyring`, never in config files
- **Audit manifests** — each run produces a manifest recording record counts and field coverage

## Quick Start

### Prerequisites
- Python 3.11+
- macOS (Keychain credential storage)
- Jira Cloud instance with read access

### Installation
```bash
git clone https://github.com/saagpatel/JSMTicketAnalyticsExport
cd JSMTicketAnalyticsExport
pip install -r requirements.txt
```

### Usage
```bash
# Store credentials in Keychain on first run
python setup_keychain.py

# Export previous calendar month (default)
python jsm_export.py

# Export a specific month
python jsm_export.py --month 2026-02

# Backfill all history (splits into monthly files by year-month under ~/Analytics/JSM/)
python jsm_export.py --backfill

# Dry run — count tickets without writing files
python jsm_export.py --dry-run --month 2026-02
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| HTTP | requests (raw REST, no PyJira) |
| Credentials | keyring — macOS Keychain |
| Output formats | CSV, JSON |
| Scheduling | macOS launchd (plist included) |

## License

MIT
