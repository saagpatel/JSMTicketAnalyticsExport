"""Tests for all_time_appender.append_to_all_time."""

import json
from pathlib import Path

from all_time_appender import append_to_all_time
from models import TicketRow


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def _make_ticket(**overrides) -> TicketRow:
    """Return a TicketRow with sensible defaults, overridable via kwargs."""
    defaults = dict(
        ticket_id="IT-0001",
        summary="Default summary",
        url="https://your-org.atlassian.net/browse/IT-0001",
        issue_type="Task",
        priority="Medium",
        labels=[],
        components=[],
        status="Open",
        resolution=None,
        resolution_time_days=None,
        assignee="Test User",
        assignee_email="test@example.com",
        reporter="Reporter",
        reporter_email="reporter@example.com",
        division=None,
        manager=None,
        created_date="2026-01-01T00:00:00.000+0000",
        updated_date="2026-01-02T00:00:00.000+0000",
        resolved_date=None,
        sla_breached=None,
        sla_time_to_resolution_mins=None,
    )
    defaults.update(overrides)
    return TicketRow(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCreatesFileIfNotExists:
    def test_creates_file_if_not_exists(self, tmp_path: Path) -> None:
        out = tmp_path / "all-time.json"
        rows = [
            _make_ticket(ticket_id="IT-0001"),
            _make_ticket(ticket_id="IT-0002", url="https://your-org.atlassian.net/browse/IT-0002"),
        ]

        append_to_all_time(rows, out)

        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert len(data) == 2
        ids = {r["ticket_id"] for r in data}
        assert ids == {"IT-0001", "IT-0002"}


class TestAppendsWithoutDuplicates:
    def test_appends_new_ticket_and_keeps_existing(self, tmp_path: Path) -> None:
        out = tmp_path / "all-time.json"

        # Seed with IT-0001 and IT-0002
        initial = [
            _make_ticket(ticket_id="IT-0001"),
            _make_ticket(ticket_id="IT-0002", url="https://your-org.atlassian.net/browse/IT-0002"),
        ]
        with out.open("w", encoding="utf-8") as fh:
            import dataclasses
            json.dump([dataclasses.asdict(r) for r in initial], fh)

        # Append IT-0002 (duplicate) + IT-0003 (new)
        append_to_all_time(
            [
                _make_ticket(ticket_id="IT-0002", url="https://your-org.atlassian.net/browse/IT-0002"),
                _make_ticket(ticket_id="IT-0003", url="https://your-org.atlassian.net/browse/IT-0003"),
            ],
            out,
        )

        data = json.loads(out.read_text(encoding="utf-8"))
        assert len(data) == 3
        ids = {r["ticket_id"] for r in data}
        assert ids == {"IT-0001", "IT-0002", "IT-0003"}


class TestIdempotentRerun:
    def test_idempotent_rerun(self, tmp_path: Path) -> None:
        out = tmp_path / "all-time.json"
        rows = [
            _make_ticket(ticket_id="IT-0001"),
            _make_ticket(ticket_id="IT-0002", url="https://your-org.atlassian.net/browse/IT-0002"),
        ]

        append_to_all_time(rows, out)
        first_count = len(json.loads(out.read_text(encoding="utf-8")))

        append_to_all_time(rows, out)
        second_count = len(json.loads(out.read_text(encoding="utf-8")))

        assert first_count == second_count == 2


class TestSortedByCreatedDate:
    def test_sorted_by_created_date(self, tmp_path: Path) -> None:
        out = tmp_path / "all-time.json"
        rows = [
            _make_ticket(ticket_id="IT-0003", created_date="2026-03-01T00:00:00.000+0000",
                         url="https://your-org.atlassian.net/browse/IT-0003"),
            _make_ticket(ticket_id="IT-0001", created_date="2026-01-01T00:00:00.000+0000"),
            _make_ticket(ticket_id="IT-0002", created_date="2026-02-01T00:00:00.000+0000",
                         url="https://your-org.atlassian.net/browse/IT-0002"),
        ]

        append_to_all_time(rows, out)

        data = json.loads(out.read_text(encoding="utf-8"))
        dates = [r["created_date"] for r in data]
        assert dates == sorted(dates)


class TestUpdatedTicketOverwrites:
    def test_updated_ticket_overwrites_old_summary(self, tmp_path: Path) -> None:
        out = tmp_path / "all-time.json"

        import dataclasses
        old_row = _make_ticket(ticket_id="IT-0001", summary="Old summary")
        with out.open("w", encoding="utf-8") as fh:
            json.dump([dataclasses.asdict(old_row)], fh)

        new_row = _make_ticket(ticket_id="IT-0001", summary="New summary")
        append_to_all_time([new_row], out)

        data = json.loads(out.read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0]["summary"] == "New summary"
