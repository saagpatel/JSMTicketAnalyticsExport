# JSM Ticket Analytics Export — Implementation Roadmap

## Architecture

### System Overview
```
macOS launchd (monthly trigger)
        │
        ▼
  jsm_export.py (CLI entrypoint)
        │
        ├─► field_resolver.py     → /rest/api/3/field (dynamic field ID lookup)
        │
        ├─► jira_client.py        → /rest/api/3/search (paginated JQL queries)
        │         │
        │    [raw ticket pages]
        │
        ├─► transformer.py        → flat TicketRow schema
        │
        ├─► writer.py             → ~/Analytics/JSM/YYYY-MM.csv
        │                           ~/Analytics/JSM/YYYY-MM.json
        │                           ~/Analytics/JSM/YYYY-MM-manifest.json
        │
        └─► all_time_appender.py  → ~/Analytics/JSM/all-time.json (append-only)
```

### File Structure
```
jsm-analytics-export/
├── jsm_export.py           # CLI entrypoint — argparse, orchestration
├── jira_client.py          # API wrapper: auth, pagination, retry logic
├── field_resolver.py       # Dynamic field ID resolution from /field endpoint
├── transformer.py          # Raw Jira ticket → TicketRow dataclass
├── writer.py               # CSV + JSON + manifest file output
├── all_time_appender.py    # Append new rows to all-time.json
├── models.py               # TicketRow dataclass + ExportManifest dataclass
├── config.py               # Non-secret config (instance URL, project key, output dir)
├── setup_keychain.py       # One-time helper: store API token in macOS Keychain
├── requirements.txt
├── com.example.jsm-export.plist  # launchd plist template
├── tests/
│   ├── test_transformer.py
│   ├── test_field_resolver.py
│   └── fixtures/
│       ├── sample_ticket.json      # realistic Jira API response
│       └── sample_field_list.json  # /rest/api/3/field response snapshot
├── CLAUDE.md
└── IMPLEMENTATION-ROADMAP.md
```

### Data Models

```python
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

@dataclass
class TicketRow:
    # Identity
    ticket_id: str              # e.g. "IT-4821"
    summary: str
    url: str                    # https://your-org.atlassian.net/browse/IT-4821

    # Classification
    issue_type: str             # Bug, Service Request, Incident, Task, etc.
    priority: str               # Highest, High, Medium, Low, Lowest
    labels: list[str]           # flattened to comma-joined string in CSV
    components: list[str]       # flattened to comma-joined string in CSV

    # Status & Resolution
    status: str                 # To Do, In Progress, Done, etc.
    resolution: Optional[str]   # None if unresolved
    resolution_time_days: Optional[float]  # None if unresolved

    # People
    assignee: Optional[str]     # display name
    assignee_email: Optional[str]
    reporter: str               # display name
    reporter_email: Optional[str]

    # Custom fields (resolved dynamically)
    division: Optional[str]     # customfield_10102 resolved value
    manager: Optional[str]      # customfield_10113 resolved value

    # Dates (ISO 8601 strings in CSV/JSON)
    created_date: str
    updated_date: str
    resolved_date: Optional[str]

    # SLA (populated if SLA fields present, else None)
    sla_breached: Optional[bool]
    sla_time_to_resolution_mins: Optional[int]


@dataclass
class ExportManifest:
    run_date: str               # ISO 8601 UTC
    date_range_start: str       # earliest created_date in this export
    date_range_end: str         # latest created_date in this export
    row_count: int
    jql_query: str              # exact JQL used for this run
    fields_exported: list[str]  # column names in output CSV
    custom_fields_resolved: dict[str, str]  # {"Division": "customfield_10102", ...}
    output_files: list[str]     # absolute paths written
    errors: list[str]           # non-fatal errors encountered (missing fields, etc.)
    duration_seconds: float


@dataclass
class FieldMapping:
    field_id: str               # "customfield_10102"
    field_name: str             # "Division"
    field_type: str             # "option", "string", "user", etc.
```

### API Contracts

**Jira REST API v3 — External:**

| Endpoint | Method | Auth | Rate Limit | Purpose |
|----------|--------|------|------------|---------|
| `https://your-org.atlassian.net/rest/api/3/field` | GET | Basic (email + API token) | 10 req/s | Resolve custom field IDs by name |
| `https://your-org.atlassian.net/rest/api/3/search` | GET | Basic (email + API token) | 10 req/s | Paginated JQL ticket export |
| `https://your-org.atlassian.net/rest/api/3/myself` | GET | Basic (email + API token) | 10 req/s | Auth validation check on startup |

**Pagination contract for `/rest/api/3/search`:**
```
GET /rest/api/3/search?jql={JQL}&startAt={N}&maxResults=100&fields={field_ids}

Response shape:
{
  "startAt": int,
  "maxResults": int,
  "total": int,        ← use this to determine page count
  "issues": [...]
}

Loop: startAt += 100 until startAt >= total
Rate limit: sleep 0.125s between requests (8 req/s target)
429 handling: exponential backoff starting at 2s, max 5 retries
```

**Credential storage via keyring:**
```python
# Write (one-time setup):
keyring.set_password("jsm-analytics", "api-token", token)
keyring.set_password("jsm-analytics", "email", email)

# Read (every run):
token = keyring.get_password("jsm-analytics", "api-token")
email = keyring.get_password("jsm-analytics", "email")
```

### Dependencies

```bash
pip install requests keyring
```

```
# requirements.txt
requests==2.31.0
keyring==24.3.0
```

No other third-party dependencies. All output (CSV, JSON) uses stdlib modules.

---

## Scope Boundaries

**In scope:**
- Full paginated export of all IT project tickets via JQL
- Dynamic resolution of Division and Manager custom field IDs
- Flat CSV + JSON output with the TicketRow schema
- Export manifest (audit trail per run)
- Append to cumulative all-time.json
- macOS launchd scheduling (monthly, 1st of month at 6am)
- One-time keychain setup helper script
- Rate limiting (8 req/s token bucket) + retry with exponential backoff
- CLI flags: `--month YYYY-MM`, `--since YYYY-MM-DD`, `--dry-run`, `--verbose`, `--backfill`

**Out of scope:**
- Dashboard / visualization (separate Claude.ai artifact project)
- Slack integration (deferred to Unified Slack IT Bot project)
- Email delivery of exports
- Multi-project export (IT project only)
- Windows or Linux scheduling

**Deferred to future phases:**
- SLA field extraction (Phase 1 — pending field ID verification)
- Automated Slack posting after export (separate project)
- Google Sheets direct write (Phase 2 if needed)

---

## Security & Credentials

- API token stored in macOS Keychain via `keyring` — never in `.env`, config files, or source code
- `setup_keychain.py` prompts interactively for email + token, writes to Keychain, exits — never logs the token
- `config.py` contains only non-secret config: instance URL, project key, output directory, JQL defaults
- Output files written to `~/Analytics/JSM/` — local only, never transmitted
- `all-time.json` contains ticket data — treat as sensitive, do not commit to git
- `.gitignore` must include: `~/Analytics/`, `*.csv`, `*.json` (data files), but NOT `manifest.json` pattern (manifests are metadata, OK to commit if desired)

---

## Phase 0: Foundation + Core Export (Days 1–3)

**Objective:** Working end-to-end export — auth validates, all IT tickets paginate correctly, flat CSV output is written with standard fields only (no custom fields yet), manifest generated.

**Tasks:**

1. **Scaffold project structure** — create all files listed in File Structure with stubs. `requirements.txt` pinned. `config.py` populated with instance URL, project key, output dir.
   - **Acceptance:** `python jsm_export.py --dry-run` runs without import errors.

2. **`setup_keychain.py`** — interactive one-time credential store. Prompts for email + API token, writes to macOS Keychain via `keyring`, then validates auth by calling `/rest/api/3/myself`.
   - **Acceptance:** Run `python setup_keychain.py` → enter creds → see `✓ Auth validated: [your name]`.

3. **`jira_client.py`** — `api_get(path, params)` wrapper with:
   - Basic auth from Keychain
   - Token bucket rate limiter (8 req/s)
   - Retry with exponential backoff (2s, 4s, 8s, 16s, 32s — max 5 retries on 429 or 5xx)
   - Returns parsed JSON or raises `JiraAPIError`
   - **Acceptance:** Unit test calls `api_get("/rest/api/3/myself")` → returns dict with `"displayName"` key.

4. **Paginated export loop in `jira_client.py`** — `get_all_issues(jql, fields)` generator that yields raw issue dicts. Uses `startAt` cursor until `startAt >= total`. Logs progress: `Fetched 1000/5432 tickets...`
   - **Acceptance:** `python jsm_export.py --dry-run --month 2026-02` logs correct total ticket count from JSM, exits without writing files.

5. **`models.py`** — define `TicketRow` and `ExportManifest` dataclasses exactly as specced above.
   - **Acceptance:** `python -c "from models import TicketRow, ExportManifest; print('OK')"` exits 0.

6. **`transformer.py`** — `transform(raw_issue: dict, field_mapping: dict) -> TicketRow`. Handles:
   - Null-safe access for all optional fields
   - Date parsing to ISO 8601 strings
   - `resolution_time_days` computed from `created` → `resolutiondate` when both present
   - Custom fields populated from `field_mapping` dict (pass empty dict in Phase 0 — custom fields will be `None`)
   - **Acceptance:** `tests/test_transformer.py` with `fixtures/sample_ticket.json` — all 15 fields populate correctly, null fields return `None` not `KeyError`.

7. **`writer.py`** — `write_csv(rows, path)` and `write_json(rows, path)` and `write_manifest(manifest, path)`.
   - CSV: `csv.DictWriter` with `TicketRow` field order as headers. Lists (labels, components) joined with `|` separator.
   - JSON: `json.dumps([dataclasses.asdict(r) for r in rows])` with indent=2.
   - Manifest: JSON with `ExportManifest` fields.
   - **Acceptance:** Write 3 sample `TicketRow` objects → open CSV in Excel (or `head`) → see correct headers and data rows.

8. **`jsm_export.py` entrypoint** — argparse CLI wiring:
   - `--month YYYY-MM` (default: previous calendar month)
   - `--since YYYY-MM-DD` (export from date to now — for backfill)
   - `--dry-run` (paginate + count, no file writes)
   - `--verbose` (DEBUG logging)
   - `--backfill` (export all tickets ever — no date filter)
   - Orchestrates: field_resolver → jira_client → transformer → writer → all_time_appender
   - **Acceptance:** `python jsm_export.py --month 2026-02` → writes `~/Analytics/JSM/2026-02.csv`, `~/Analytics/JSM/2026-02.json`, `~/Analytics/JSM/2026-02-manifest.json`. Open CSV, verify row count matches manifest `row_count`.

**Verification checklist:**
- [ ] `python setup_keychain.py` → `✓ Auth validated: [name]`
- [ ] `python jsm_export.py --dry-run --month 2026-02` → logs ticket count, exits 0
- [ ] `python jsm_export.py --month 2026-02` → 3 files created in `~/Analytics/JSM/`
- [ ] CSV opens in Numbers/Excel with correct headers, no encoding errors
- [ ] Manifest JSON parses clean: `python -c "import json; print(json.load(open('~/Analytics/JSM/2026-02-manifest.json'))['row_count'])"`
- [ ] `python -m pytest tests/` → all tests pass

**Risks:**
- JSM instance uses cookie auth or SSO rather than API tokens → Mitigation: test auth against `/rest/api/3/myself` before any export logic. Fallback: switch to OAuth 2.0 flow (document but don't implement yet).
- `total` count from `/search` doesn't match actual paginated rows (JSM bug with some JQL filters) → Mitigation: count rows in the generator, warn if mismatch > 0.1%.

---

## Phase 1: Custom Fields + SLA (Days 4–5)

**Objective:** Dynamic field ID resolution for Division and Manager. SLA breach data extracted if available. all-time.json append working.

**Tasks:**

1. **`field_resolver.py`** — `resolve_fields(target_names: list[str]) -> dict[str, FieldMapping]`. Calls `/rest/api/3/field`, filters by name match (case-insensitive), returns `{field_name: FieldMapping}`. Warns to stdout for any unresolved names.
   - **Acceptance:** `python -c "from field_resolver import resolve_fields; print(resolve_fields(['Division', 'Manager']))"` → returns dict with correct `customfield_XXXXX` IDs.

2. **Wire custom fields into transformer** — update `transform()` to accept `field_mapping` and populate `division` and `manager` from the resolved field IDs.
   - **Acceptance:** `tests/test_transformer.py` — add fixture with populated custom fields → verify `division` and `manager` fields in output `TicketRow`.

3. **SLA field detection** — in `field_resolver.py`, also attempt to resolve `"Time to resolution"` and `"Time to first response"` SLA fields. If found, extract `completedCycles[0].breached` (bool) and `completedCycles[0].elapsedTime.millis` into `sla_breached` and `sla_time_to_resolution_mins`.
   - **Acceptance:** Run full export → open CSV → `sla_breached` column populated (or all `None` if SLA fields absent — not an error).

4. **`all_time_appender.py`** — `append_to_all_time(new_rows: list[TicketRow], path: Path)`. Loads existing `all-time.json` (empty list if not exists), deduplicates by `ticket_id`, appends new rows, writes back.
   - **Acceptance:** Run export for Feb 2026, then March 2026 → `all-time.json` contains combined rows, no duplicates, sorted by `created_date`.

**Verification checklist:**
- [ ] Export CSV has `division` and `manager` columns populated (spot-check 5 tickets in JSM UI)
- [ ] `all-time.json` exists at `~/Analytics/JSM/all-time.json` after two runs
- [ ] Re-running same month doesn't duplicate rows in `all-time.json`
- [ ] Manifest `custom_fields_resolved` shows `{"Division": "customfield_10102", "Manager": "customfield_10113"}`

**Risks:**
- SLA fields not exposed via REST API (depends on JSM Service Management configuration) → Mitigation: treat as optional — if `/rest/api/3/field` doesn't return them, log a warning, leave `sla_*` fields as `None`. Don't block Phase 1 completion on SLA.

---

## Phase 2: Scheduling + Backfill (Day 6)

**Objective:** launchd plist installed and verified. Full historical backfill completed. Project is operational for recurring monthly use.

**Tasks:**

1. **launchd plist** — create `com.example.jsm-export.plist` targeting `python /path/to/jsm_export.py --month auto` on the 1st of each month at 06:00. Include `StandardOutPath` and `StandardErrorPath` pointing to `~/Analytics/JSM/logs/`.
   - **Acceptance:** `launchctl load ~/Library/LaunchAgents/com.example.jsm-export.plist` → `launchctl list | grep jsm` shows entry. Verify with `launchctl start com.example.jsm-export` → export runs, log file written.

2. **`--month auto` mode** — when `--month auto` is passed (used by launchd), derive previous calendar month automatically. E.g., if today is 2026-04-01, export `2026-03`.
   - **Acceptance:** `python jsm_export.py --month auto --dry-run` on March 24 → logs "Exporting 2026-02..." (previous full month).

3. **Historical backfill** — run `python jsm_export.py --backfill` to export all tickets from project inception. This may take 10–30 minutes on a large instance. Progress logging every 500 tickets. Creates one JSON/CSV per calendar month in output dir (loop over months in Python).
   - **Acceptance:** `~/Analytics/JSM/` contains one CSV per month back to project start date. `all-time.json` row count matches sum of all monthly CSVs minus duplicates.

4. **README.md** — installation guide covering: Python setup, `pip install`, `setup_keychain.py`, launchd install, manual test run.

**Verification checklist:**
- [ ] `launchctl list | grep jsm` shows the job loaded
- [ ] Manual trigger via `launchctl start` produces correct output files
- [ ] `~/Analytics/JSM/` has monthly CSVs from backfill
- [ ] `all-time.json` row count is reasonable (cross-check against JSM dashboard total)
- [ ] Logs write to `~/Analytics/JSM/logs/` without permission errors
