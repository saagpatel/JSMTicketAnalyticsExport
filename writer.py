"""Writes TicketRow lists and ExportManifest to CSV and JSON files."""

import csv
import dataclasses
import json
import logging
from pathlib import Path

from models import ExportManifest, TicketRow

logger = logging.getLogger(__name__)

# Field order mirrors the dataclass declaration; derived once at import time so
# every write call uses a consistent, stable column order.
_TICKET_FIELDNAMES: list[str] = [f.name for f in dataclasses.fields(TicketRow)]


def write_csv(rows: list[TicketRow], path: Path) -> Path:
    """Serialise a list of TicketRow objects to a CSV file.

    List fields (``labels``, ``components``) are joined with ``|``.
    ``sla_breached`` is written as "true", "false", or "" (never Python booleans).

    Args:
        rows: Ticket rows to write.
        path: Destination file path.  Parent directories are created if absent.

    Returns:
        The resolved path of the written file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Writing %d rows to CSV: %s", len(rows), path)

    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_TICKET_FIELDNAMES, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow(_ticket_to_csv_dict(row))

    logger.debug("CSV write complete: %s", path)
    return path


def write_json(rows: list[TicketRow], path: Path) -> Path:
    """Serialise a list of TicketRow objects to a pretty-printed JSON file.

    Args:
        rows: Ticket rows to write.
        path: Destination file path.  Parent directories are created if absent.

    Returns:
        The resolved path of the written file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Writing %d rows to JSON: %s", len(rows), path)

    payload = [dataclasses.asdict(r) for r in rows]
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)

    logger.debug("JSON write complete: %s", path)
    return path


def write_manifest(manifest: ExportManifest, path: Path) -> Path:
    """Serialise an ExportManifest to a pretty-printed JSON file.

    Args:
        manifest: The manifest to write.
        path: Destination file path.  Parent directories are created if absent.

    Returns:
        The resolved path of the written file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Writing manifest to: %s", path)

    with path.open("w", encoding="utf-8") as fh:
        json.dump(dataclasses.asdict(manifest), fh, indent=2, ensure_ascii=False)

    logger.debug("Manifest write complete: %s", path)
    return path


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _ticket_to_csv_dict(row: TicketRow) -> dict[str, str]:
    """Convert a TicketRow to a flat string dict suitable for csv.DictWriter.

    - list fields joined with ``|``
    - ``sla_breached``: True → "true", False → "false", None → ""
    - All other None values written as ""
    """
    d: dict = dataclasses.asdict(row)

    # Encode list fields
    d["labels"] = "|".join(row.labels)
    d["components"] = "|".join(row.components)

    # Encode sla_breached as lowercase string or empty
    if row.sla_breached is True:
        d["sla_breached"] = "true"
    elif row.sla_breached is False:
        d["sla_breached"] = "false"
    else:
        d["sla_breached"] = ""

    # Coerce remaining None values to empty string for clean CSV output
    return {k: ("" if v is None else v) for k, v in d.items()}
