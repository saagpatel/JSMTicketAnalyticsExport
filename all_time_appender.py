"""Append new rows to cumulative all-time.json.

Deduplicates by ticket_id — existing entries are overwritten with the
latest data; new tickets are inserted.  Output is sorted by created_date
ascending so the file is stable and diff-friendly.
"""

import dataclasses
import json
import logging
from pathlib import Path

from models import TicketRow

log = logging.getLogger(__name__)


def append_to_all_time(new_rows: list[TicketRow], path: Path) -> None:
    """Merge new_rows into the cumulative all-time JSON file at path.

    - Loads existing records from path (if it exists).
    - Overwrites any record whose ticket_id matches a row in new_rows.
    - Inserts records for ticket_ids not yet present.
    - Writes the result back sorted by created_date ascending.
    - Creates parent directories if they do not exist.
    """
    if path.exists():
        with path.open(encoding="utf-8") as fh:
            raw: list[dict] = json.load(fh)
    else:
        raw = []

    existing: dict[str, dict] = {r["ticket_id"]: r for r in raw}

    new_count = 0
    updated_count = 0

    for row in new_rows:
        record = dataclasses.asdict(row)
        ticket_id: str = record["ticket_id"]
        if ticket_id in existing:
            existing[ticket_id] = record
            updated_count += 1
        else:
            existing[ticket_id] = record
            new_count += 1

    sorted_list = sorted(existing.values(), key=lambda r: r.get("created_date", ""))

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(sorted_list, fh, indent=2, ensure_ascii=False)

    log.info(
        "all-time.json: %d added, %d updated, %d total",
        new_count,
        updated_count,
        len(sorted_list),
    )
