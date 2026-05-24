from __future__ import annotations

import csv
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, Sequence

from .models import PostDraft
from .store import ContentStore

ExportFormat = Literal["json", "csv"]


@dataclass(frozen=True)
class ExportResult:
    path: Path
    count: int
    format: ExportFormat


@dataclass(frozen=True)
class DraftFolderExportResult:
    path: Path
    count: int
    batch_id: str


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
            "batch_id",
            "post_type",
            "platform_targets",
            "trend_title",
            "caption",
            "hashtags",
            "selected_asset_ids",
            "overlay_text",
            "edit_notes",
            "status",
        ]
        with output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    else:
        raise ValueError(f"Unsupported export format: {format}")

    return ExportResult(path=output, count=len(rows), format=format)


def export_draft_folders(
    store: ContentStore,
    batch_id: str,
    output_dir: str | Path,
) -> DraftFolderExportResult:
    """Export a complete human-reviewable folder for every post draft in a batch."""

    posts = store.list_post_drafts(batch_id)
    assets_by_id = {str(asset["asset_id"]): asset for asset in store.list_assets()}
    batch = next((candidate for candidate in store.list_batches() if candidate.id == batch_id), None)
    if batch is None:
        raise KeyError(batch_id)

    day = datetime.fromtimestamp(batch.created_at).strftime("%Y-%m-%d")
    output = Path(output_dir).expanduser() / day
    output.mkdir(parents=True, exist_ok=True)

    trend_snapshot = [
        {
            "post_id": post.id,
            "post_type": post.post_type,
            "platform_targets": post.platform_targets,
            "trend_title": post.trend_title,
            "caption": post.caption,
            "hashtags": post.hashtags,
            "overlay_text": post.overlay_text,
            "edit_notes": post.edit_notes,
        }
        for post in posts
    ]
    (output / "trend-research.json").write_text(
        json.dumps(trend_snapshot, indent=2) + "\n",
        encoding="utf-8",
    )
    (output / "run-summary.md").write_text(_run_summary(batch_id, posts), encoding="utf-8")

    for index, post in enumerate(posts, start=1):
        post_dir = output / _post_folder_name(index, post.post_type)
        if post_dir.exists():
            shutil.rmtree(post_dir)
        media_dir = post_dir / "media"
        media_dir.mkdir(parents=True, exist_ok=True)

        selected_assets = [assets_by_id[asset_id] for asset_id in post.selected_asset_ids if asset_id in assets_by_id]
        exported_media = []
        for asset in selected_assets:
            source = Path(str(asset["absolute_path"])).expanduser()
            if post.post_type == "video":
                exported_media.append(_export_video_draft(source, media_dir))
            else:
                exported_media.append(_copy_asset(source, media_dir))

        (post_dir / "caption.md").write_text(post.caption.strip() + "\n", encoding="utf-8")
        (post_dir / "hashtags.txt").write_text(" ".join(post.hashtags).strip() + "\n", encoding="utf-8")
        (post_dir / "edit_notes.md").write_text(post.edit_notes.strip() + "\n", encoding="utf-8")
        (post_dir / "post.json").write_text(
            json.dumps(
                {
                    "id": post.id,
                    "batch_id": post.batch_id,
                    "post_type": post.post_type,
                    "platform_targets": post.platform_targets,
                    "trend_title": post.trend_title,
                    "caption": post.caption,
                    "hashtags": post.hashtags,
                    "overlay_text": post.overlay_text,
                    "edit_notes": post.edit_notes,
                    "status": post.status,
                    "media": [path.name for path in exported_media],
                    "source_asset_ids": post.selected_asset_ids,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    return DraftFolderExportResult(path=output, count=len(posts), batch_id=batch_id)


def _run_summary(batch_id: str, posts: Sequence[PostDraft]) -> str:
    lines = [f"# Rafa daily draft run", "", f"Batch: `{batch_id}`", "", "## Drafts", ""]
    for index, post in enumerate(posts, start=1):
        lines.append(f"{index}. {post.post_type}: {post.trend_title}")
    return "\n".join(lines) + "\n"


def _post_folder_name(index: int, post_type: str) -> str:
    suffix = "reel-tiktok" if post_type == "video" else "instagram-photo"
    return f"{index:02d}-{suffix}"


def _copy_asset(source: Path, media_dir: Path) -> Path:
    destination = media_dir / source.name
    shutil.copy2(source, destination)
    return destination


def _export_video_draft(source: Path, media_dir: Path) -> Path:
    draft_path = media_dir / "draft.mp4"
    if _try_ffmpeg_trim(source, draft_path):
        return draft_path
    return _copy_asset(source, media_dir)


def _try_ffmpeg_trim(source: Path, output_path: Path) -> bool:
    if shutil.which("ffmpeg") is None:
        return False
    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-t",
        "12",
        "-vf",
        "scale=1080:-2:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-an",
        str(output_path),
    ]
    try:
        completed = subprocess.run(command, check=False, capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        output_path.unlink(missing_ok=True)
        return False
    if completed.returncode != 0 or not output_path.exists():
        output_path.unlink(missing_ok=True)
        return False
    return True
