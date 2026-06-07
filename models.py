"""Data models for JSM Ticket Analytics Export."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TicketRow:
    """Flat representation of a single JSM ticket for CSV/JSON export."""

    # Identity
    ticket_id: str              # e.g. "IT-4821"
    summary: str
    url: str                    # https://your-org.atlassian.net/browse/IT-4821

    # Classification
    issue_type: str             # Bug, Service Request, Incident, Task, etc.
    priority: str               # Highest, High, Medium, Low, Lowest
    labels: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)

    # Status & Resolution
    status: str = ""
    resolution: Optional[str] = None
    resolution_time_days: Optional[float] = None

    # People
    assignee: Optional[str] = None
    assignee_email: Optional[str] = None
    reporter: str = ""
    reporter_email: Optional[str] = None

    # Custom fields (resolved dynamically — Phase 1)
    division: Optional[str] = None
    manager: Optional[str] = None

    # Dates (ISO 8601 strings)
    created_date: str = ""
    updated_date: str = ""
    resolved_date: Optional[str] = None

    # SLA (Phase 1 — populated if SLA fields present)
    sla_breached: Optional[bool] = None
    sla_time_to_resolution_mins: Optional[int] = None


@dataclass
class ExportManifest:
    """Audit trail metadata for a single export run."""

    run_date: str                                   # ISO 8601 UTC
    date_range_start: str                           # earliest created_date in export
    date_range_end: str                             # latest created_date in export
    row_count: int
    jql_query: str
    fields_exported: list[str] = field(default_factory=list)
    custom_fields_resolved: dict[str, str] = field(default_factory=dict)
    output_files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


@dataclass
class FieldMapping:
    """Maps a human-readable field name to its Jira custom field ID."""

    field_id: str       # "customfield_10102"
    field_name: str     # "Division"
    field_type: str     # "option", "string", "user", etc.
