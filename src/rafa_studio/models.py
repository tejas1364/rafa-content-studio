from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".webp"}
VIDEO_EXTENSIONS = {".mov", ".mp4", ".m4v"}
SUPPORTED_EXTENSIONS = PHOTO_EXTENSIONS | VIDEO_EXTENSIONS


@dataclass(frozen=True)
class MediaAsset:
    id: str
    filename: str
    absolute_path: str
    relative_path: str
    media_type: str
    size_bytes: int
    modified_at: float

    @classmethod
    def from_path(cls, path: Path, root: Path) -> "MediaAsset":
        resolved_root = root.expanduser().resolve()
        resolved_path = path.expanduser().resolve()
        relative_path = resolved_path.relative_to(resolved_root).as_posix()
        stat = resolved_path.stat()
        media_type = "photo" if resolved_path.suffix.lower() in PHOTO_EXTENSIONS else "video"
        stable_key = f"{relative_path}:{stat.st_size}:{int(stat.st_mtime)}"
        asset_id = hashlib.sha256(stable_key.encode("utf-8")).hexdigest()[:16]
        return cls(
            id=asset_id,
            filename=resolved_path.name,
            absolute_path=str(resolved_path),
            relative_path=relative_path,
            media_type=media_type,
            size_bytes=stat.st_size,
            modified_at=stat.st_mtime,
        )


@dataclass(frozen=True)
class ContentDraft:
    id: str
    asset_id: str
    caption: str
    status: str = "pending"


@dataclass(frozen=True)
class TrendIdea:
    id: str
    title: str
    platform: str
    format_hint: str
    caption_angle: str
    hashtags: list[str]


@dataclass(frozen=True)
class ContentBatch:
    id: str
    created_at: float
    status: str
    target_post_count: int = 4


@dataclass(frozen=True)
class PostDraft:
    id: str
    batch_id: str
    post_type: str
    platform_targets: list[str]
    trend_title: str
    caption: str
    hashtags: list[str]
    selected_asset_ids: list[str]
    overlay_text: list[str]
    edit_notes: str
    status: str = "pending"
