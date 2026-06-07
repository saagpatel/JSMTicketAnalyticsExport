"""Tests for transformer.transform() — pure function, no mocks needed."""

import json
from pathlib import Path

import pytest

from models import FieldMapping
from transformer import transform

_FIXTURES = Path(__file__).parent / "fixtures"


def _load(filename: str) -> dict:
    with (_FIXTURES / filename).open() as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _division_mapping() -> dict[str, FieldMapping]:
    return {
        "division": FieldMapping(
            field_id="customfield_10102",
            field_name="Division",
            field_type="option",
        ),
        "manager": FieldMapping(
            field_id="customfield_10113",
            field_name="Manager",
            field_type="user",
        ),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTransformResolvedTicket:
    """All 15+ fields on a fully-resolved ticket."""

    def setup_method(self):
        self.row = transform(_load("sample_ticket.json"), {})

    def test_ticket_id(self):
        assert self.row.ticket_id == "IT-4821"

    def test_summary(self):
        assert self.row.summary == "Laptop replacement request — Finance team"

    def test_url_contains_browse_key(self):
        assert "/browse/IT-4821" in self.row.url

    def test_issue_type(self):
        assert self.row.issue_type == "Service Request"

    def test_priority(self):
        assert self.row.priority == "Medium"

    def test_labels(self):
        assert self.row.labels == ["hardware", "finance"]

    def test_components(self):
        assert self.row.components == ["Endpoints", "Procurement"]

    def test_status(self):
        assert self.row.status == "Done"

    def test_resolution(self):
        assert self.row.resolution == "Done"

    def test_assignee(self):
        assert self.row.assignee == "Alex Rivera"

    def test_assignee_email_contains_name(self):
        assert self.row.assignee_email is not None
        assert "alex.rivera" in self.row.assignee_email

    def test_reporter(self):
        assert self.row.reporter == "Jordan Chen"

    def test_created_date_non_empty(self):
        assert self.row.created_date != ""

    def test_resolved_date_non_empty(self):
        assert self.row.resolved_date is not None
        assert self.row.resolved_date != ""

    def test_resolution_time_days_positive(self):
        assert self.row.resolution_time_days is not None
        assert self.row.resolution_time_days > 0

    def test_division_none_without_mapping(self):
        assert self.row.division is None

    def test_manager_none_without_mapping(self):
        assert self.row.manager is None


class TestTransformUnresolvedTicket:
    """Fields that should be absent or empty on an open ticket."""

    def setup_method(self):
        self.row = transform(_load("sample_ticket_unresolved.json"), {})

    def test_assignee_is_none(self):
        assert self.row.assignee is None

    def test_assignee_email_is_none(self):
        assert self.row.assignee_email is None

    def test_resolution_is_none(self):
        assert self.row.resolution is None

    def test_resolved_date_is_none(self):
        assert self.row.resolved_date is None

    def test_resolution_time_days_is_none(self):
        assert self.row.resolution_time_days is None

    def test_labels_empty(self):
        assert self.row.labels == []

    def test_components_empty(self):
        assert self.row.components == []

    def test_status_in_progress(self):
        assert self.row.status == "In Progress"


class TestTransformWithFieldMapping:
    """Custom fields are extracted when a field_mapping is provided."""

    def setup_method(self):
        self.row = transform(_load("sample_ticket.json"), _division_mapping())

    def test_division_extracted(self):
        assert self.row.division == "Finance"

    def test_manager_extracted(self):
        assert self.row.manager == "Dana Kim"


class TestTransformMissingFields:
    """Minimal input dict — no exceptions, sensible defaults."""

    def setup_method(self):
        self.row = transform({"key": "IT-1", "fields": {}}, {})

    def test_no_exception_raised(self):
        # Reaching here means no exception was raised during transform.
        assert self.row is not None

    def test_ticket_id_is_key(self):
        assert self.row.ticket_id == "IT-1"

    def test_optional_fields_are_none(self):
        assert self.row.assignee is None
        assert self.row.assignee_email is None
        assert self.row.resolution is None
        assert self.row.resolved_date is None
        assert self.row.resolution_time_days is None
        assert self.row.division is None
        assert self.row.manager is None
        assert self.row.reporter_email is None
        assert self.row.sla_breached is None
        assert self.row.sla_time_to_resolution_mins is None

    def test_required_strings_are_empty(self):
        assert self.row.summary == ""
        assert self.row.status == ""
        assert self.row.reporter == ""
        assert self.row.created_date == ""


class TestResolutionTimeDaysCalculation:
    """Resolution time arithmetic: 2026-02-03T09:14:22Z → 2026-02-10T16:45:33Z ≈ 7.313 days."""

    def test_resolution_time_days_approx(self):
        row = transform(_load("sample_ticket.json"), {})
        assert row.resolution_time_days is not None
        assert abs(row.resolution_time_days - 7.313) < 0.5


class TestSlaExtraction:
    """SLA fields extracted from completedCycles when field_mapping includes SLA."""

    def _sla_mapping(self) -> dict[str, FieldMapping]:
        return {
            **_division_mapping(),
            "time to resolution": FieldMapping(
                field_id="customfield_10200",
                field_name="Time to resolution",
                field_type="sla",
            ),
        }

    def test_sla_breached_extracted(self):
        row = transform(_load("sample_ticket.json"), self._sla_mapping())
        assert row.sla_breached is False

    def test_sla_time_to_resolution_mins_extracted(self):
        row = transform(_load("sample_ticket.json"), self._sla_mapping())
        # 172800000 ms = 2880 minutes = 48 hours
        assert row.sla_time_to_resolution_mins == 2880

    def test_sla_none_without_mapping(self):
        row = transform(_load("sample_ticket.json"), {})
        assert row.sla_breached is None
        assert row.sla_time_to_resolution_mins is None

    def test_sla_none_with_empty_completed_cycles(self):
        ticket = _load("sample_ticket.json")
        ticket["fields"]["customfield_10200"] = {"completedCycles": []}
        row = transform(ticket, self._sla_mapping())
        assert row.sla_breached is None
        assert row.sla_time_to_resolution_mins is None

    def test_sla_none_when_field_absent(self):
        ticket = _load("sample_ticket_unresolved.json")
        row = transform(ticket, self._sla_mapping())
        assert row.sla_breached is None
        assert row.sla_time_to_resolution_mins is None
