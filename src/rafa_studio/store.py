from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import ContentDraft, MediaAsset


class ContentStore:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path).expanduser()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS assets (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    absolute_path TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    modified_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS drafts (
                    id TEXT PRIMARY KEY,
                    asset_id TEXT NOT NULL,
                    caption TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    FOREIGN KEY(asset_id) REFERENCES assets(id)
                );
                """
            )

    def upsert_asset(self, asset: MediaAsset) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO assets (
                    id, filename, absolute_path, relative_path, media_type, size_bytes, modified_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    filename = excluded.filename,
                    absolute_path = excluded.absolute_path,
                    relative_path = excluded.relative_path,
                    media_type = excluded.media_type,
                    size_bytes = excluded.size_bytes,
                    modified_at = excluded.modified_at
                """,
                (
                    asset.id,
                    asset.filename,
                    asset.absolute_path,
                    asset.relative_path,
                    asset.media_type,
                    asset.size_bytes,
                    asset.modified_at,
                ),
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO drafts (id, asset_id, caption, status)
                VALUES (?, ?, ?, 'pending')
                """,
                (f"draft-{asset.id}", asset.id, generate_caption(asset)),
            )

    def upsert_assets(self, assets: list[MediaAsset]) -> int:
        for asset in assets:
            self.upsert_asset(asset)
        return len(assets)

    def list_assets_with_drafts(self) -> list[dict[str, str | int | float]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    assets.id AS asset_id,
                    assets.filename,
                    assets.relative_path,
                    assets.media_type,
                    assets.size_bytes,
                    drafts.id AS draft_id,
                    drafts.caption,
                    drafts.status
                FROM assets
                LEFT JOIN drafts ON drafts.asset_id = assets.id
                ORDER BY assets.relative_path COLLATE NOCASE
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def list_drafts(self) -> list[ContentDraft]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, asset_id, caption, status FROM drafts ORDER BY id"
            ).fetchall()
        return [ContentDraft(**dict(row)) for row in rows]

    def get_draft(self, draft_id: str) -> ContentDraft:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, asset_id, caption, status FROM drafts WHERE id = ?",
                (draft_id,),
            ).fetchone()
        if row is None:
            raise KeyError(draft_id)
        return ContentDraft(**dict(row))

    def set_draft_status(self, draft_id: str, status: str) -> ContentDraft:
        if status not in {"pending", "approved", "rejected"}:
            raise ValueError(f"Unsupported draft status: {status}")
        with self._connect() as connection:
            connection.execute("UPDATE drafts SET status = ? WHERE id = ?", (status, draft_id))
        return self.get_draft(draft_id)

    def set_caption(self, draft_id: str, caption: str) -> ContentDraft:
        cleaned_caption = caption.strip()
        if not cleaned_caption:
            raise ValueError("Caption cannot be empty")
        with self._connect() as connection:
            connection.execute("UPDATE drafts SET caption = ? WHERE id = ?", (cleaned_caption, draft_id))
        return self.get_draft(draft_id)


def generate_caption(asset: MediaAsset) -> str:
    stem = Path(asset.filename).stem.replace("-", " ").replace("_", " ").strip()
    if not stem:
        stem = "today"
    return f"Rafa update: {stem}. Tiny dog, major main-character energy."
