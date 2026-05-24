from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .store import ContentStore

ExportFormat = Literal["json", "csv"]


@dataclass(frozen=True)
class ExportResult:
    path: Path
    count: int
    format: ExportFormat


def export_approved_drafts(
    store: ContentStore,
    output_path: str | Path,
    *,
    format: ExportFormat = "json",
) -> ExportResult:
    output = Path(output_path).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = store.list_drafts_for_export(status="approved")

    if format == "json":
        output.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    elif format == "csv":
        fieldnames = [
            "draft_id",
            "asset_id",
            "filename",
            "absolute_path",
            "relative_path",
            "media_type",
            "caption",
            "status",
        ]
        with output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    else:
        raise ValueError(f"Unsupported export format: {format}")

    return ExportResult(path=output, count=len(rows), format=format)
