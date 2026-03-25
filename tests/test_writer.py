"""Tests for writer.write_csv, write_json, and write_manifest."""

import csv
import json
from pathlib import Path

import pytest

from models import ExportManifest, TicketRow
from writer import write_csv, write_json, write_manifest


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def _make_ticket(**overrides) -> TicketRow:
    """Return a TicketRow with sensible defaults, overridable via kwargs."""
    defaults = dict(
        ticket_id="IT-0001",
        summary="Default summary",
        url="https://servicedesk.inside-box.net/browse/IT-0001",
        issue_type="Task",
        priority="Medium",
        labels=[],
        components=[],
        status="Open",
        resolution=None,
        resolution_time_days=None,
        assignee="Test User",
        assignee_email="test.user@inside-box.net",
        reporter="Reporter Name",
        reporter_email="reporter@inside-box.net",
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
# write_csv
# ---------------------------------------------------------------------------

class TestWriteCsvCreatesFile:
    def test_file_exists_with_correct_line_count(self, tmp_path):
        rows = [_make_ticket(ticket_id="IT-0001"), _make_ticket(ticket_id="IT-0002")]
        out = tmp_path / "tickets.csv"
        write_csv(rows, out)

        assert out.exists()
        lines = out.read_text(encoding="utf-8").splitlines()
        # header + 2 data rows
        assert len(lines) == 3

    def test_header_contains_expected_columns(self, tmp_path):
        out = tmp_path / "tickets.csv"
        write_csv([_make_ticket()], out)

        with out.open(encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            fieldnames = reader.fieldnames or []

        for col in ("ticket_id", "summary", "status", "assignee", "created_date"):
            assert col in fieldnames


class TestWriteCsvListFieldsPipeSeparated:
    def test_labels_joined_with_pipe(self, tmp_path):
        row = _make_ticket(labels=["a", "b", "c"])
        out = tmp_path / "tickets.csv"
        write_csv([row], out)

        with out.open(encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            record = next(reader)

        assert record["labels"] == "a|b|c"

    def test_components_joined_with_pipe(self, tmp_path):
        row = _make_ticket(components=["Alpha", "Beta"])
        out = tmp_path / "tickets.csv"
        write_csv([row], out)

        with out.open(encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            record = next(reader)

        assert record["components"] == "Alpha|Beta"


class TestWriteCsvNoneFieldsEmptyString:
    def test_resolution_none_written_as_empty_string(self, tmp_path):
        row = _make_ticket(resolution=None)
        out = tmp_path / "tickets.csv"
        write_csv([row], out)

        with out.open(encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            record = next(reader)

        assert record["resolution"] == ""
        assert record["resolution"] != "None"

    def test_assignee_none_written_as_empty_string(self, tmp_path):
        row = _make_ticket(assignee=None)
        out = tmp_path / "tickets.csv"
        write_csv([row], out)

        with out.open(encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            record = next(reader)

        assert record["assignee"] == ""


class TestWriteCsvSlaBreachedEncoding:
    def test_true_written_as_lowercase_true(self, tmp_path):
        row = _make_ticket(sla_breached=True)
        out = tmp_path / "tickets.csv"
        write_csv([row], out)

        with out.open(encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            record = next(reader)

        assert record["sla_breached"] == "true"

    def test_false_written_as_lowercase_false(self, tmp_path):
        row = _make_ticket(sla_breached=False)
        out = tmp_path / "tickets.csv"
        write_csv([row], out)

        with out.open(encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            record = next(reader)

        assert record["sla_breached"] == "false"

    def test_none_written_as_empty_string(self, tmp_path):
        row = _make_ticket(sla_breached=None)
        out = tmp_path / "tickets.csv"
        write_csv([row], out)

        with out.open(encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            record = next(reader)

        assert record["sla_breached"] == ""


# ---------------------------------------------------------------------------
# write_json
# ---------------------------------------------------------------------------

class TestWriteJsonRoundTrip:
    def test_row_count_and_ticket_ids(self, tmp_path):
        rows = [
            _make_ticket(ticket_id="IT-0010"),
            _make_ticket(ticket_id="IT-0011"),
        ]
        out = tmp_path / "tickets.json"
        write_json(rows, out)

        assert out.exists()
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert len(payload) == 2
        ids = {r["ticket_id"] for r in payload}
        assert ids == {"IT-0010", "IT-0011"}

    def test_json_is_valid_list(self, tmp_path):
        out = tmp_path / "tickets.json"
        write_json([_make_ticket()], out)
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert isinstance(payload, list)


# ---------------------------------------------------------------------------
# write_manifest
# ---------------------------------------------------------------------------

class TestWriteManifest:
    def test_manifest_fields_round_trip(self, tmp_path):
        manifest = ExportManifest(
            run_date="2026-03-24T00:00:00Z",
            date_range_start="2026-01-01",
            date_range_end="2026-03-24",
            row_count=42,
            jql_query='project = IT ORDER BY created ASC',
            fields_exported=["ticket_id", "summary"],
            output_files=["tickets.csv", "tickets.json"],
        )
        out = tmp_path / "manifest.json"
        write_manifest(manifest, out)

        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["row_count"] == 42
        assert data["jql_query"] == 'project = IT ORDER BY created ASC'
        assert data["run_date"] == "2026-03-24T00:00:00Z"

    def test_manifest_output_files_preserved(self, tmp_path):
        manifest = ExportManifest(
            run_date="2026-03-24T00:00:00Z",
            date_range_start="2026-01-01",
            date_range_end="2026-03-24",
            row_count=1,
            jql_query="project = IT",
            output_files=["tickets.csv"],
        )
        out = tmp_path / "manifest.json"
        write_manifest(manifest, out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["output_files"] == ["tickets.csv"]


# ---------------------------------------------------------------------------
# Directory creation
# ---------------------------------------------------------------------------

class TestWriteCreatesParentDirs:
    def test_csv_creates_nested_dirs(self, tmp_path):
        deep_path = tmp_path / "nested" / "deep" / "file.csv"
        write_csv([_make_ticket()], deep_path)
        assert deep_path.exists()

    def test_json_creates_nested_dirs(self, tmp_path):
        deep_path = tmp_path / "nested" / "deep" / "file.json"
        write_json([_make_ticket()], deep_path)
        assert deep_path.exists()

    def test_manifest_creates_nested_dirs(self, tmp_path):
        manifest = ExportManifest(
            run_date="2026-03-24T00:00:00Z",
            date_range_start="2026-01-01",
            date_range_end="2026-03-24",
            row_count=0,
            jql_query="project = IT",
        )
        deep_path = tmp_path / "nested" / "deep" / "manifest.json"
        write_manifest(manifest, deep_path)
        assert deep_path.exists()
