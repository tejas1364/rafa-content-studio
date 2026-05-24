from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StudioSettings:
    """Runtime settings for the local-first studio."""

    media_dir: str = os.environ.get(
        "RAFA_MEDIA_DIR",
        str(Path.home() / "Pictures" / "Rafa iCloud Album"),
    )
    database_path: str = os.environ.get(
        "RAFA_STUDIO_DB",
        str(Path.home() / ".rafa-content-studio" / "studio.sqlite3"),
    )

    @property
    def media_path(self) -> Path:
        return Path(self.media_dir).expanduser()

    @property
    def db_path(self) -> Path:
        return Path(self.database_path).expanduser()
