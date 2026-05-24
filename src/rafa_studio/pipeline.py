from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .batch import ManualTrendProvider, generate_daily_batch
from .export import DraftFolderExportResult, export_draft_folders
from .ingest import scan_media_directory
from .store import ContentStore


@dataclass(frozen=True)
class DailyRunResult:
    assets_imported: int
    batch_id: str
    post_count: int
    output_path: Path


def run_daily(
    *,
    store: ContentStore,
    media_dir: str | Path,
    output_dir: str | Path,
    trend_titles: list[str] | None = None,
) -> DailyRunResult:
    """Scan media, generate today's six-post batch, and export draft folders."""

    media_path = Path(media_dir).expanduser()
    assets = scan_media_directory(media_path)
    imported = store.upsert_assets(assets)
    batch = generate_daily_batch(store, ManualTrendProvider(trend_titles))
    export_result: DraftFolderExportResult = export_draft_folders(store, batch.id, output_dir)
    return DailyRunResult(
        assets_imported=imported,
        batch_id=batch.id,
        post_count=export_result.count,
        output_path=export_result.path,
    )
