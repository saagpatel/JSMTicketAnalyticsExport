"""Dynamic field ID resolution from /rest/api/3/field.

Calls the Jira field metadata endpoint and maps human-readable field names
to their custom field IDs and types.
"""

import logging
from models import FieldMapping
from jira_client import api_get

log = logging.getLogger(__name__)


def resolve_fields(target_names: list[str]) -> dict[str, FieldMapping]:
    """Resolve custom field names to their Jira field IDs.

    Calls /rest/api/3/field and matches each target name case-insensitively
    against the returned field list. Missing names are logged as warnings
    rather than raising exceptions.

    Args:
        target_names: Human-readable field names to resolve, e.g. ["Division", "Manager"].

    Returns:
        Dict keyed by target_name.lower() → FieldMapping. Unresolved names
        are omitted from the result.
    """
    if not target_names:
        return {}

    fields: list[dict] = api_get("/rest/api/3/field")

    # Build a lookup from lowercase name → field dict for O(1) matching.
    name_index: dict[str, dict] = {f["name"].lower(): f for f in fields}

    result: dict[str, FieldMapping] = {}
    for target_name in target_names:
        key = target_name.lower()
        field = name_index.get(key)
        if field is None:
            log.warning("Field not found in Jira metadata: %r", target_name)
            continue
        schema_type = field.get("schema", {}).get("type", "unknown")
        result[key] = FieldMapping(
            field_id=field["id"],
            field_name=field["name"],
            field_type=schema_type,
        )

    return result
