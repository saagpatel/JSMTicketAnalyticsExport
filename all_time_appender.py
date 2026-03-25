"""Append new rows to cumulative all-time.json.

Phase 0: no-op stub.
Phase 1: full dedup + append logic with ticket_id-based deduplication.
"""

import logging
from pathlib import Path

from models import TicketRow

log = logging.getLogger(__name__)


def append_to_all_time(new_rows: list[TicketRow], path: Path) -> None:
    """Append new ticket rows to the cumulative all-time JSON file.

    Phase 0: logs a skip message and returns.
    Phase 1 will implement dedup by ticket_id and sorted append.
    """
    log.info("all_time_appender: skipped (Phase 1)")
