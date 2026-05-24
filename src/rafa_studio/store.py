from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import ContentBatch, ContentDraft, MediaAsset, PostDraft


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

                CREATE TABLE IF NOT EXISTS content_batches (
                    id TEXT PRIMARY KEY,
                    created_at REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft',
                    target_post_count INTEGER NOT NULL DEFAULT 4
                );

                CREATE TABLE IF NOT EXISTS post_drafts (
                    id TEXT PRIMARY KEY,
                    batch_id TEXT NOT NULL,
                    post_type TEXT NOT NULL,
                    platform_targets TEXT NOT NULL,
                    trend_title TEXT NOT NULL,
                    caption TEXT NOT NULL,
                    hashtags TEXT NOT NULL,
                    selected_asset_ids TEXT NOT NULL,
                    overlay_text TEXT NOT NULL,
                    edit_notes TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    FOREIGN KEY(batch_id) REFERENCES content_batches(id)
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

    def upsert_assets(self, assets: list[MediaAsset]) -> int:
        for asset in assets:
            self.upsert_asset(asset)
        return len(assets)

    def list_assets(self) -> list[dict[str, str | int | float]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id AS asset_id, filename, absolute_path, relative_path, media_type,
                       size_bytes, modified_at
                FROM assets
                ORDER BY media_type DESC, relative_path COLLATE NOCASE
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def list_assets_with_drafts(self) -> list[dict[str, str | int | float | None]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    assets.id AS asset_id,
                    assets.filename,
                    assets.absolute_path,
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

    def list_drafts_for_export(self, status: str = "approved") -> list[dict[str, str | int | float]]:
        return self.list_post_drafts_for_export(status=status)

    def list_post_drafts_for_export(self, status: str = "approved") -> list[dict[str, str | int | float]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM post_drafts
                WHERE status = ?
                ORDER BY batch_id DESC, id COLLATE NOCASE
                """,
                (status,),
            ).fetchall()
        return [_post_row_to_export_dict(row) for row in rows]

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

    def create_batch(self, batch: ContentBatch) -> ContentBatch:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO content_batches (id, created_at, status, target_post_count)
                VALUES (?, ?, ?, ?)
                """,
                (batch.id, batch.created_at, batch.status, batch.target_post_count),
            )
        return batch

    def list_batches(self) -> list[ContentBatch]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, created_at, status, target_post_count
                FROM content_batches
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [ContentBatch(**dict(row)) for row in rows]

    def latest_batch(self) -> ContentBatch | None:
        batches = self.list_batches()
        return batches[0] if batches else None

    def add_post_draft(self, post: PostDraft) -> PostDraft:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO post_drafts (
                    id, batch_id, post_type, platform_targets, trend_title, caption, hashtags,
                    selected_asset_ids, overlay_text, edit_notes, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post.id,
                    post.batch_id,
                    post.post_type,
                    json.dumps(post.platform_targets),
                    post.trend_title,
                    post.caption,
                    json.dumps(post.hashtags),
                    json.dumps(post.selected_asset_ids),
                    json.dumps(post.overlay_text),
                    post.edit_notes,
                    post.status,
                ),
            )
        return post

    def list_post_drafts(self, batch_id: str | None = None) -> list[PostDraft]:
        sql = "SELECT * FROM post_drafts"
        params: tuple[str, ...] = ()
        if batch_id is not None:
            sql += " WHERE batch_id = ?"
            params = (batch_id,)
        sql += " ORDER BY id COLLATE NOCASE"
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [_post_row_to_model(row) for row in rows]

    def list_post_draft_cards(self, batch_id: str | None = None) -> list[dict[str, object]]:
        posts = self.list_post_drafts(batch_id=batch_id)
        assets_by_id = {str(asset["asset_id"]): asset for asset in self.list_assets()}
        cards: list[dict[str, object]] = []
        for post in posts:
            cards.append(
                {
                    "id": post.id,
                    "batch_id": post.batch_id,
                    "post_type": post.post_type,
                    "platform_targets": post.platform_targets,
                    "trend_title": post.trend_title,
                    "caption": post.caption,
                    "hashtags": post.hashtags,
                    "selected_assets": [
                        assets_by_id[asset_id]
                        for asset_id in post.selected_asset_ids
                        if asset_id in assets_by_id
                    ],
                    "overlay_text": post.overlay_text,
                    "edit_notes": post.edit_notes,
                    "status": post.status,
                }
            )
        return cards

    def get_post_draft(self, post_id: str) -> PostDraft:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM post_drafts WHERE id = ?", (post_id,)).fetchone()
        if row is None:
            raise KeyError(post_id)
        return _post_row_to_model(row)

    def set_post_status(self, post_id: str, status: str) -> PostDraft:
        if status not in {"pending", "approved", "rejected"}:
            raise ValueError(f"Unsupported post status: {status}")
        with self._connect() as connection:
            connection.execute("UPDATE post_drafts SET status = ? WHERE id = ?", (status, post_id))
        return self.get_post_draft(post_id)

    def set_post_caption(self, post_id: str, caption: str) -> PostDraft:
        cleaned_caption = caption.strip()
        if not cleaned_caption:
            raise ValueError("Caption cannot be empty")
        with self._connect() as connection:
            connection.execute("UPDATE post_drafts SET caption = ? WHERE id = ?", (cleaned_caption, post_id))
        return self.get_post_draft(post_id)


def generate_caption(asset: MediaAsset) -> str:
    stem = Path(asset.filename).stem.replace("-", " ").replace("_", " ").strip()
    if not stem:
        stem = "today"
    return f"Rafa update: {stem}. Tiny dog, major main-character energy."


def _post_row_to_model(row: sqlite3.Row) -> PostDraft:
    data = dict(row)
    return PostDraft(
        id=data["id"],
        batch_id=data["batch_id"],
        post_type=data["post_type"],
        platform_targets=json.loads(data["platform_targets"]),
        trend_title=data["trend_title"],
        caption=data["caption"],
        hashtags=json.loads(data["hashtags"]),
        selected_asset_ids=json.loads(data["selected_asset_ids"]),
        overlay_text=json.loads(data["overlay_text"]),
        edit_notes=data["edit_notes"],
        status=data["status"],
    )


def _post_row_to_export_dict(row: sqlite3.Row) -> dict[str, str | int | float]:
    post = _post_row_to_model(row)
    return {
        "draft_id": post.id,
        "batch_id": post.batch_id,
        "post_type": post.post_type,
        "platform_targets": ",".join(post.platform_targets),
        "trend_title": post.trend_title,
        "caption": post.caption,
        "hashtags": " ".join(post.hashtags),
        "selected_asset_ids": ",".join(post.selected_asset_ids),
        "overlay_text": " | ".join(post.overlay_text),
        "edit_notes": post.edit_notes,
        "status": post.status,
    }
