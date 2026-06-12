# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.1.0] - 2026-06-07

### Added
- Initial public release.
- Paginated export of all Jira Service Management tickets via the REST API, bypassing the native 1,000-row export cap.
- CSV and JSON output plus a per-run audit manifest (row counts, resolved field IDs, exact JQL, timing).
- `--month`, `--since`, `--backfill`, `--dry-run`, and `--verbose` CLI modes; backfill auto-splits output into per-month files.
- Dynamic custom-field ID resolution by name.
- API credentials stored in the OS keychain via `keyring`.
- `jsm-export` and `jsm-export-setup` console entry points; packaged for PyPI.
