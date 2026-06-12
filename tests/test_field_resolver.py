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
