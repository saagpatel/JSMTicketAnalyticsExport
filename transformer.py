"""Transforms raw Jira API issue dicts into TicketRow dataclasses."""

import logging
from datetime import datetime, timezone
from typing import Any

from config import JIRA_INSTANCE
from models import FieldMapping, TicketRow

logger = logging.getLogger(__name__)

_ISO_FORMATS = (
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S%z",
)


def _safe_get(d: dict, *keys: str, default: Any = None) -> Any:
    """Traverse nested dicts by key path; return default on any missing key or non-dict node."""
    current: Any = d
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, None)
        if current is None:
            return default
    return current


def _parse_iso_date(date_str: str | None) -> str | None:
    """Pass through a non-empty ISO 8601 string, or return None."""
    if not date_str:
        return None
    return date_str


def _parse_datetime(date_str: str | None) -> datetime | None:
    """Parse an ISO 8601 date string into an aware datetime, or return None."""
    if not date_str:
        return None
    for fmt in _ISO_FORMATS:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    logger.warning("Could not parse date string: %r", date_str)
    return None


def _compute_resolution_days(created: str, resolved: str | None) -> float | None:
    """Return elapsed days between created and resolved as a float, or None if either is absent."""
    if not resolved:
        return None
    dt_created = _parse_datetime(created)
    dt_resolved = _parse_datetime(resolved)
    if dt_created is None or dt_resolved is None:
        return None
    # Ensure both are timezone-aware for safe subtraction
    if dt_created.tzinfo is None:
        dt_created = dt_created.replace(tzinfo=timezone.utc)
    if dt_resolved.tzinfo is None:
        dt_resolved = dt_resolved.replace(tzinfo=timezone.utc)
    delta = dt_resolved - dt_created
    return delta.total_seconds() / 86400.0


def _extract_sla(raw_value: Any, issue_key: str) -> tuple[bool | None, int | None]:
    """Extract SLA breach status and resolution time from a Jira SLA field.

    Expected shape::

        {"completedCycles": [{"breached": false, "elapsedTime": {"millis": 172800000}}]}

    Returns (sla_breached, sla_time_to_resolution_mins) or (None, None) if absent.
    """
    if not isinstance(raw_value, dict):
        return None, None

    cycles: list[dict] = raw_value.get("completedCycles") or []
    if not cycles:
        logger.debug("SLA field on %s has no completedCycles", issue_key)
        return None, None

    cycle = cycles[0]
    breached: bool | None = cycle.get("breached")
    millis: int | None = _safe_get(cycle, "elapsedTime", "millis")
    minutes: int | None = int(millis / 60_000) if millis is not None else None

    return breached, minutes


def transform(raw_issue: dict, field_mapping: dict[str, FieldMapping]) -> TicketRow:
    """Transform a single element from the Jira /search issues array into a TicketRow.

    Args:
        raw_issue: A dict with at minimum ``key`` and ``fields`` keys as returned by
                   the Jira REST API v3 /rest/api/3/search endpoint.
        field_mapping: Mapping of logical name (e.g. "division") to FieldMapping
                       describing how to extract the custom field value.  Pass an
                       empty dict during Phase 0; custom fields will be left None.

    Returns:
        A fully populated TicketRow (with None for any field absent in the API response).
    """
    key: str = raw_issue.get("key", "")
    fields: dict = raw_issue.get("fields") or {}

    logger.debug("Transforming issue %s", key)

    # ---- Dates ------------------------------------------------------------------
    created_raw: str = fields.get("created") or ""
    updated_raw: str = fields.get("updated") or ""
    resolved_raw: str | None = fields.get("resolutiondate") or None

    created_date = _parse_iso_date(created_raw)
    updated_date = _parse_iso_date(updated_raw)
    resolved_date = _parse_iso_date(resolved_raw)
    resolution_time_days = _compute_resolution_days(created_raw, resolved_raw)

    # ---- People -----------------------------------------------------------------
    assignee_obj: dict | None = fields.get("assignee")
    assignee: str | None = _safe_get(assignee_obj or {}, "displayName") if assignee_obj else None
    assignee_email: str | None = _safe_get(assignee_obj or {}, "emailAddress") if assignee_obj else None

    reporter_obj: dict | None = fields.get("reporter")
    reporter: str = _safe_get(reporter_obj or {}, "displayName", default="") if reporter_obj else ""
    reporter_email: str | None = _safe_get(reporter_obj or {}, "emailAddress") if reporter_obj else None

    # ---- Classification ---------------------------------------------------------
    components_raw: list[dict] = fields.get("components") or []
    components: list[str] = [c["name"] for c in components_raw if isinstance(c, dict) and "name" in c]

    labels: list[str] = fields.get("labels") or []

    # ---- Custom fields ----------------------------------------------------------
    division: str | None = None
    manager: str | None = None
    sla_breached: bool | None = None
    sla_time_to_resolution_mins: int | None = None

    for logical_name, mapping in field_mapping.items():
        field_id = mapping.field_id
        raw_value: Any = fields.get(field_id)

        if raw_value is None:
            logger.debug("Custom field %s (%s) absent on issue %s", logical_name, field_id, key)
            continue

        # SLA fields have a special shape with completedCycles
        if logical_name.lower() == "time to resolution":
            sla_breached, sla_time_to_resolution_mins = _extract_sla(raw_value, key)
            continue

        extracted: str | None = None
        if isinstance(raw_value, dict):
            if "value" in raw_value:
                # Option-type field: {"value": "Engineering", "id": "10001"}
                extracted = raw_value["value"]
            elif "displayName" in raw_value:
                # User-type field: {"displayName": "Jane Smith", "emailAddress": "..."}
                extracted = raw_value["displayName"]
            else:
                logger.warning(
                    "Unrecognised custom field shape for %s on issue %s: %r",
                    field_id,
                    key,
                    raw_value,
                )
        elif isinstance(raw_value, str):
            extracted = raw_value
        else:
            logger.warning(
                "Unexpected type %s for custom field %s on issue %s",
                type(raw_value).__name__,
                field_id,
                key,
            )

        if logical_name.lower() == "division":
            division = extracted
        elif logical_name.lower() == "manager":
            manager = extracted
        else:
            logger.debug("Unmapped logical custom field name %r — skipping", logical_name)

    return TicketRow(
        # Identity
        ticket_id=key,
        summary=fields.get("summary") or "",
        url=f"{JIRA_INSTANCE}/browse/{key}",
        # Classification
        issue_type=_safe_get(fields, "issuetype", "name", default=""),
        priority=_safe_get(fields, "priority", "name", default=""),
        labels=labels,
        components=components,
        # Status & Resolution
        status=_safe_get(fields, "status", "name", default=""),
        resolution=_safe_get(fields, "resolution", "name"),
        resolution_time_days=resolution_time_days,
        # People
        assignee=assignee,
        assignee_email=assignee_email,
        reporter=reporter,
        reporter_email=reporter_email,
        # Custom fields
        division=division,
        manager=manager,
        # Dates
        created_date=created_date or "",
        updated_date=updated_date or "",
        resolved_date=resolved_date,
        # SLA
        sla_breached=sla_breached,
        sla_time_to_resolution_mins=sla_time_to_resolution_mins,
    )
