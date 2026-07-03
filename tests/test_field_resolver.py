"""Tests for field_resolver.resolve_fields."""

import json
import logging
from pathlib import Path
from unittest.mock import patch

from field_resolver import resolve_fields

_FIXTURES = Path(__file__).parent / "fixtures"


def _load_fields() -> list[dict]:
    with (_FIXTURES / "sample_field_list.json").open() as fh:
        return json.load(fh)


@patch("field_resolver.api_get")
def test_resolves_division_and_manager(mock_api_get):
    mock_api_get.return_value = _load_fields()

    result = resolve_fields(["Division", "Manager"])

    assert "division" in result
    assert result["division"].field_id == "customfield_10102"
    assert "manager" in result
    assert result["manager"].field_id == "customfield_10113"


@patch("field_resolver.api_get")
def test_case_insensitive(mock_api_get):
    mock_api_get.return_value = _load_fields()

    result = resolve_fields(["division", "MANAGER"])

    assert result["division"].field_id == "customfield_10102"
    assert result["manager"].field_id == "customfield_10113"


@patch("field_resolver.api_get")
def test_unresolved_name_warns_and_returns_partial(mock_api_get, caplog):
    mock_api_get.return_value = _load_fields()

    with caplog.at_level(logging.WARNING, logger="field_resolver"):
        result = resolve_fields(["Division", "NonexistentField"])

    assert "division" in result
    assert "nonexistentfield" not in result
    assert any("NonexistentField" in msg for msg in caplog.messages)


@patch("field_resolver.api_get")
def test_empty_list_returns_empty_dict_no_api_call(mock_api_get):
    result = resolve_fields([])

    assert result == {}
    mock_api_get.assert_not_called()


@patch("field_resolver.api_get")
def test_field_type_extracted(mock_api_get):
    mock_api_get.return_value = _load_fields()

    result = resolve_fields(["Division", "Manager"])

    assert result["division"].field_type == "option"
    assert result["manager"].field_type == "user"


@patch("field_resolver.api_get")
def test_full_mapping_contract(mock_api_get):
    """Acceptance: FieldMapping carries exact field_id, canonical field_name, and field_type from API.

    field_name must reflect what the API returned, not the caller's casing — this is what
    populates ExportManifest.custom_fields_resolved and downstream column headers.
    """
    mock_api_get.return_value = _load_fields()

    result = resolve_fields(["division", "manager"])

    div = result["division"]
    assert div.field_id == "customfield_10102"
    assert div.field_name == "Division"  # canonical casing from API, not caller input
    assert div.field_type == "option"

    mgr = result["manager"]
    assert mgr.field_id == "customfield_10113"
    assert mgr.field_name == "Manager"
    assert mgr.field_type == "user"


@patch("field_resolver.api_get")
def test_field_with_no_schema_key_defaults_to_unknown(mock_api_get):
    """Edge: field without a schema key (some Jira system fields) resolves with field_type='unknown'."""
    mock_api_get.return_value = [{"id": "customfield_99999", "name": "Orphaned"}]

    result = resolve_fields(["Orphaned"])

    assert result["orphaned"].field_id == "customfield_99999"
    assert result["orphaned"].field_type == "unknown"


@patch("field_resolver.api_get")
def test_duplicate_field_names_last_occurrence_wins(mock_api_get):
    """Edge: if the API returns two fields with the same name, the last one wins.

    Atlassian can return duplicate display names when a custom field exists across multiple
    JSM service projects. The resolver must not crash; it silently keeps the last entry.
    """
    mock_api_get.return_value = [
        {"id": "customfield_00001", "name": "Division", "schema": {"type": "option"}},
        {"id": "customfield_00002", "name": "Division", "schema": {"type": "option"}},
    ]

    result = resolve_fields(["Division"])

    assert result["division"].field_id == "customfield_00002"
