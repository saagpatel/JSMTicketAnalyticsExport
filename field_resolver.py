"""Dynamic field ID resolution from /rest/api/3/field.

Phase 0: returns empty mapping.
Phase 1: resolves custom fields by name from the Jira field metadata endpoint.
"""

import logging
from models import FieldMapping

log = logging.getLogger(__name__)


def resolve_fields(target_names: list[str]) -> dict[str, FieldMapping]:
    """Resolve custom field names to their Jira field IDs.

    In Phase 0, pass an empty list to get an empty mapping.
    Phase 1 will implement the actual API call to /rest/api/3/field.
    """
    if not target_names:
        return {}
    raise NotImplementedError(
        "Custom field resolution is Phase 1 — pass an empty list for Phase 0"
    )
