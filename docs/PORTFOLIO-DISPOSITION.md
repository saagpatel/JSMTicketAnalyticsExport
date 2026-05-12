# JSM Ticket Analytics Export — Portfolio Disposition

**Status:** Active (operator-tool, scheduled CLI with launchd) —
Python 3.11+ CLI that exports Jira Service Management tickets via
the REST API, **bypassing Jira's native 1,000-row export cap** on
`origin/main`. Produces per-month CSV and JSON datasets plus
audit manifests. **macOS Keychain credential storage via
`keyring`** + rate-limited + retry-wrapped API client + monthly
file splits in backfill mode + `com.saagar.jsm-export.plist`
launchd scheduling. **Fourth operator-tool / dogfood cluster
member**; introduces new sub-shape: **scheduled-CLI-with-launchd**.

> Disposition uses strict `origin/main` verification.
> **Operator-tool cluster reaches 4 with 4 distinct sub-shapes.**

---

## Verification posture

Only `origin` (`saagpatel/JSMTicketAnalyticsExport`). Clean.

`origin/main`:

- Tip: `a93ce13` chore(deps): bump requests to 2.33.0 to fix 3 CVEs
- Recent commits are scaffolding wave + CVE bump:
  - `a93ce13` requests 2.33.0 CVE bump
  - Full OSS scaffolding (CHANGELOG, PR/issue templates, CoC,
    Makefile, Dependabot, contributing, security policy, MIT,
    README)
- Repo tree (`origin/main`):
  - `all_time_appender.py` (backfill / append logic)
  - `config.py`
  - `com.saagar.jsm-export.plist` (launchd scheduled execution)
  - `IMPLEMENTATION-ROADMAP.md`
  - Standard scaffolding
- **No `pyproject.toml`** — uses `requirements.txt`. Not PyPI-
  distributed (clone-and-run).
- Default branch: `main`

---

## Current state in one paragraph

JSM Ticket Analytics Export is a Python CLI that solves a
narrow-but-real Jira pain: **Jira's 1,000-row export cap is a
lie**, so this CLI paginates the REST API to retrieve every
ticket regardless of volume. Output: per-month CSV (for
Excel/Sheets analytics) + JSON (for downstream pipelines) + audit
manifests recording record counts and field coverage. Security
posture: **API token in macOS Keychain via `keyring`** (never in
plaintext config); rate-limited + retry-wrapped API client.
Backfill mode auto-splits a full export into monthly files.
**launchd plist (`com.saagar.jsm-export.plist`) on canonical
main** enables scheduled execution — the operator runs this on a
cadence against their Jira instance. Per memory: Phase 0, 48
tests. Active state because no v1 declaration and the recent
commit cadence is scaffolding + CVE bumps, not feature work.

---

## Why "Active (operator-tool, scheduled CLI with launchd)" — fourth cluster member, new sub-shape

The operator-tool / dogfood cluster reaches 4 members with 4
distinct sub-shapes:

| Member | Sub-shape | Distribution |
|---|---|---|
| GithubRepoAuditor (R11) | pure-internal, PyPI-published | `pip install github-repo-auditor` |
| AIWorkFlow (R17.2) | multi-surface with client portal | Vercel + service host + local CLI |
| NetworkMapper (R17.6) | single-user local-audit clone-and-run | clone + pip + sudo run |
| **JSMTicketAnalyticsExport** | **scheduled CLI with launchd** | **clone + pip + launchd plist** |

JSM's sub-shape distinguishes:
- **No PyPI** (like NetworkMapper) — clone-and-run only
- **No external surface** (like all operator-tool members)
- **Scheduled execution via launchd** — operator runs on cadence,
  not on-demand
- **macOS Keychain credentials** — same pattern as RoomTone
  (iOS) and ITServiceHealth (corporate-context self-hosted) for
  secure credential handling

This is **scheduled operator infrastructure**: the operator's
data-export pipeline runs on a launchd cadence against their
Jira instance, with results landing in CSV/JSON for downstream
analysis. Different from NetworkMapper (on-demand network audit)
and AIWorkFlow (interactive Slack-bot-driven). Closer to a
data-engineering ETL job than a tool.

State is Active because:
- No v1 declaration
- Recent commits are scaffolding + CVE bumps
- 48 tests per memory but Phase 0 framing suggests operator-side
  hesitation about "shipped" claim

---

## Cluster taxonomy update

| Cluster | Count | Sub-shapes |
|---|---|---|
| **Operator-tool / dogfood** | **4** | PyPI-published (GHA) / multi-surface-with-portal (AIWF) / local-audit-clone-and-run (NetMapper) / **scheduled-CLI-with-launchd (JSM)** |
| (others unchanged) | | |

Operator-tool cluster reaches 4 with 4 distinct sub-shapes —
**cluster maturity exceeds iOS App Store cluster's sub-shape
diversity at the same membership count**. This is now the
most-internally-diverse cluster in the portfolio.

---

## Unblock trigger (operator)

This is internal operator infrastructure. Operational concerns:

1. **launchd plist install workflow** — `cp com.saagar.jsm-
   export.plist ~/Library/LaunchAgents/` + `launchctl load`.
   Document.
2. **Jira API token rotation cadence** — Keychain-stored but
   eventually expires; document rotation flow.
3. **Jira REST API pagination behavior** — Atlassian periodically
   changes pagination semantics (cursor-based vs offset-based);
   verify against current Jira Cloud API version.
4. **Monthly file output disk usage** — backfill mode partitions
   by year-month; verify retention policy for older months.
5. **Audit manifest format stability** — downstream pipelines
   may depend on the manifest schema; treat as a contract.
6. **macOS Keychain access on launchd-run process** — launchd
   agents may have different Keychain access semantics than
   interactive CLI; verify the credential lookup works in
   background context.
7. **Update memory record**: "Phase 0" → substantively shipped
   operator tool with 48 tests + launchd plist + Keychain
   credentials.

Estimated operator time: ~1-2 hours for launchd verification +
memory update.

---

## Portfolio operating system instructions

| Aspect | Posture |
|---|---|
| Portfolio status | `Active (operator-tool, scheduled CLI with launchd)` |
| Audience | **Operator self** (own Jira instance) |
| Distribution | **Clone + pip install + launchd plist** (not PyPI) |
| Review cadence | Active — operator-cadence + CVE security maintenance |
| Resurface conditions | (a) Jira REST API breaking change, (b) Keychain access change on launchd-run process, (c) requests / keyring CVE, (d) `requirements.txt` dep tree drift |
| Co-batch with | Operator-tool cluster — **now 4 repos** |
| Sub-shape | **Scheduled-CLI-with-launchd** (new; operator infrastructure on a cadence) |
| Special concern | **launchd-context Keychain access.** Different semantics than interactive CLI; verify. |
| Special concern | **Jira REST API pagination behavior.** Atlassian periodically changes pagination; verify against current Cloud API. |
| Special concern | **Audit manifest schema as contract** for downstream pipelines. |
| Special concern | **Memory drift correction**: "Phase 0" → substantively shipped operator infrastructure. |

---

## Reactivation procedure

1. Verify branch tracking.
2. Review stash `r18-jsm-stash` (CLAUDE.md mod + .codex/ +
   AGENTS.md).
3. **Update memory record**: Phase 0 → operator-tool, shipped
   with 48 tests + launchd plist + Keychain credentials.
4. Verify launchd plist install: `cp com.saagar.jsm-export.plist
   ~/Library/LaunchAgents/ && launchctl load
   ~/Library/LaunchAgents/com.saagar.jsm-export.plist`.
5. Verify Jira API token still valid in Keychain.
6. Run `pytest` — expect 48 tests passing.
7. Verify pagination against current Jira Cloud API (check the
   `nextPageToken` vs `startAt` semantics).
8. Spot-check audit manifest schema against any downstream
   consumers.

---

## Last known reference

| Field | Value |
|---|---|
| `origin/main` tip | `a93ce13` chore(deps): bump requests to 2.33.0 to fix 3 CVEs |
| Default branch | `main` |
| Build system | Python 3.11+ + `keyring` (macOS Keychain) + `requests` + standard `requirements.txt` |
| Distribution | **Clone + pip install + launchd plist** (not PyPI) |
| Audience | **Operator self** (own Jira instance) |
| Test count | 48 per memory |
| Distinguishing tech | **Bypasses Jira 1,000-row export cap** + macOS Keychain credentials + monthly file splits + audit manifests + launchd scheduled execution + rate-limited retry-wrapped API client |
| Notable files | `com.saagar.jsm-export.plist` (launchd) + `all_time_appender.py` (backfill) + `config.py` |
| Migration state | No `legacy-origin` remote |
| Distinguishing feature | **Fourth operator-tool cluster member; introduces scheduled-CLI-with-launchd sub-shape.** Operator-tool cluster now has 4 distinct sub-shapes — most-internally-diverse cluster in portfolio. Memory drift correction (Phase 0 → shipped). |
