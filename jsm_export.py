"""CLI entrypoint for JSM Ticket Analytics Export.

Orchestrates: auth validation → field resolution → JQL construction →
paginated ticket fetch → transformation → file output + manifest.

Usage::

    python jsm_export.py --month 2026-02
    python jsm_export.py --since 2026-01-15
    python jsm_export.py --backfill
    python jsm_export.py --dry-run --month 2026-02
"""

import argparse
import dataclasses
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import config
from all_time_appender import append_to_all_time
from field_resolver import resolve_fields
from jira_client import JiraAPIError, get_all_issues, validate_auth
from models import ExportManifest
from transformer import transform
from writer import write_csv, write_json, write_manifest

log = logging.getLogger(__name__)

# Standard Jira fields requested in every search (custom fields added at runtime).
_STANDARD_FIELDS = [
    "summary",
    "issuetype",
    "priority",
    "labels",
    "components",
    "status",
    "resolution",
    "assignee",
    "reporter",
    "created",
    "updated",
    "resolutiondate",
]


def _previous_month() -> str:
    """Return the previous calendar month as ``YYYY-MM``."""
    today = datetime.now(tz=timezone.utc)
    if today.month == 1:
        return f"{today.year - 1}-12"
    return f"{today.year}-{today.month - 1:02d}"


def _next_month_first_day(month: str) -> str:
    """Given ``YYYY-MM``, return the first day of the following month as ``YYYY-MM-DD``."""
    year, mon = int(month[:4]), int(month[5:7])
    if mon == 12:
        return f"{year + 1}-01-01"
    return f"{year}-{mon + 1:02d}-01"


def build_jql(
    month: str | None,
    since: str | None,
    backfill: bool,
) -> str:
    """Construct a JQL query string from CLI arguments.

    Exactly one of ``month``, ``since``, or ``backfill`` should be set.
    If none are set, defaults to the previous calendar month.
    """
    base = f"project = {config.PROJECT_KEY}"
    order = config.DEFAULT_JQL_ORDER

    if backfill:
        return f"{base} {order}"

    if since:
        return f'{base} AND created >= "{since}" {order}'

    if month:
        start = f"{month}-01"
        end = _next_month_first_day(month)
        return f'{base} AND created >= "{start}" AND created < "{end}" {order}'

    # Default: previous calendar month
    return build_jql(month=_previous_month(), since=None, backfill=False)


def _resolve_month_label(
    month: str | None,
    since: str | None,
    backfill: bool,
) -> str:
    """Derive a human-readable label for file naming."""
    if backfill:
        return "all-time"
    if since:
        return f"since-{since}"
    if month:
        return month
    return _previous_month()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export JSM tickets to CSV + JSON for IT analytics.",
    )
    parser.add_argument(
        "--month",
        type=str,
        metavar="YYYY-MM",
        help='Calendar month to export. Use "auto" for previous month. (default: previous month)',
    )
    parser.add_argument(
        "--since",
        type=str,
        metavar="YYYY-MM-DD",
        help="Export all tickets created on or after this date.",
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Export all tickets ever (no date filter).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Paginate and count tickets but do not write output files.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run the JSM ticket export pipeline."""
    args = _parse_args(argv)

    # -- Logging setup --------------------------------------------------------
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    start_time = time.monotonic()

    # -- Resolve --month auto -------------------------------------------------
    month = args.month
    if month == "auto":
        month = _previous_month()
        log.info("--month auto resolved to %s", month)

    # -- Auth validation ------------------------------------------------------
    log.info("Validating Jira credentials...")
    try:
        display_name = validate_auth()
    except (JiraAPIError, RuntimeError) as exc:
        log.error("Auth validation failed: %s", exc)
        sys.exit(1)

    log.info("Authenticated as: %s", display_name)

    # -- Field resolution (Phase 0: empty) ------------------------------------
    field_mapping = resolve_fields([])
    extra_field_ids = [m.field_id for m in field_mapping.values()]
    all_fields = _STANDARD_FIELDS + extra_field_ids

    # -- JQL construction -----------------------------------------------------
    jql = build_jql(month=month, since=args.since, backfill=args.backfill)
    log.info("JQL: %s", jql)

    # -- Fetch tickets --------------------------------------------------------
    label = _resolve_month_label(month=month, since=args.since, backfill=args.backfill)
    log.info("Exporting %s...", label)

    if args.dry_run:
        count = sum(1 for _ in get_all_issues(jql, all_fields))
        log.info("Dry run complete. Ticket count: %d", count)
        return

    raw_issues = list(get_all_issues(jql, all_fields))
    log.info("Fetched %d tickets. Transforming...", len(raw_issues))

    # -- Transform ------------------------------------------------------------
    errors: list[str] = []
    rows = []
    for issue in raw_issues:
        try:
            rows.append(transform(issue, field_mapping))
        except Exception as exc:
            issue_key = issue.get("key", "unknown")
            log.warning("Failed to transform %s: %s", issue_key, exc)
            errors.append(f"Transform error on {issue_key}: {exc}")

    log.info("Transformed %d / %d tickets.", len(rows), len(raw_issues))

    # -- Write output ---------------------------------------------------------
    output_dir = config.OUTPUT_DIR
    csv_path = write_csv(rows, output_dir / f"{label}.csv")
    json_path = write_json(rows, output_dir / f"{label}.json")

    # -- Manifest -------------------------------------------------------------
    duration = time.monotonic() - start_time
    date_range_start = rows[0].created_date if rows else ""
    date_range_end = rows[-1].created_date if rows else ""

    manifest = ExportManifest(
        run_date=datetime.now(tz=timezone.utc).isoformat(),
        date_range_start=date_range_start,
        date_range_end=date_range_end,
        row_count=len(rows),
        jql_query=jql,
        fields_exported=[f.name for f in dataclasses.fields(rows[0])] if rows else [],
        custom_fields_resolved={
            m.field_name: m.field_id for m in field_mapping.values()
        },
        output_files=[str(csv_path), str(json_path)],
        errors=errors,
        duration_seconds=round(duration, 2),
    )
    manifest_path = write_manifest(manifest, output_dir / f"{label}-manifest.json")
    manifest.output_files.append(str(manifest_path))

    # -- All-time append (Phase 0: no-op) -------------------------------------
    append_to_all_time(rows, output_dir / "all-time.json")

    # -- Summary --------------------------------------------------------------
    log.info(
        "Export complete: %d tickets, %d errors, %.1fs elapsed. "
        "Files: %s",
        len(rows),
        len(errors),
        duration,
        ", ".join(manifest.output_files),
    )


if __name__ == "__main__":
    main()
