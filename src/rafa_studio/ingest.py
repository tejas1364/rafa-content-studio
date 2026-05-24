from __future__ import annotations

from pathlib import Path

from .models import MediaAsset, SUPPORTED_EXTENSIONS


def scan_media_directory(media_dir: str | Path) -> list[MediaAsset]:
    """Find supported photo/video files in a local iCloud album export/share directory."""
    root = Path(media_dir).expanduser()
    if not root.exists() or not root.is_dir():
        return []

    media_paths = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and not path.name.startswith(".")
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    media_paths.sort(key=lambda path: path.relative_to(root).as_posix().lower())
    return [MediaAsset.from_path(path, root) for path in media_paths]
