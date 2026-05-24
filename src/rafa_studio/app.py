from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .batch import ManualTrendProvider, generate_daily_batch
from .config import StudioSettings
from .export import export_approved_drafts
from .ingest import scan_media_directory
from .models import MediaAsset
from .store import ContentStore
from .thumbnails import ThumbnailService

PACKAGE_DIR = Path(__file__).parent


class CaptionUpdate(BaseModel):
    caption: str


class TrendInput(BaseModel):
    trends: list[str] | None = None


def create_app(settings: StudioSettings | None = None, store: ContentStore | None = None) -> FastAPI:
    settings = settings or StudioSettings()
    store = store or ContentStore(settings.db_path)

    app = FastAPI(title="Rafa Content Studio", version="0.2.0")
    templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))
    thumbnails = ThumbnailService(settings.thumbnail_path)
    app.mount("/static", StaticFiles(directory=str(PACKAGE_DIR / "static")), name="static")
    app.mount("/thumbnails", StaticFiles(directory=str(settings.thumbnail_path)), name="thumbnails")

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request) -> HTMLResponse:
        latest_batch = store.latest_batch()
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "settings": settings,
                "batch": latest_batch,
                "posts": _post_cards(store, thumbnails, latest_batch.id if latest_batch else None),
                "assets": _asset_cards(store, thumbnails),
            },
        )

    @app.post("/scan")
    def scan_from_dashboard() -> RedirectResponse:
        assets = scan_media_directory(settings.media_path)
        store.upsert_assets(assets)
        return RedirectResponse(url="/", status_code=303)

    @app.post("/api/scan")
    def scan() -> dict[str, int | str]:
        assets = scan_media_directory(settings.media_path)
        imported = store.upsert_assets(assets)
        return {"assets_imported": imported, "media_dir": str(settings.media_path)}

    @app.post("/generate-batch")
    def generate_batch_from_dashboard(trends_text: str = Form(default="")) -> RedirectResponse:
        trends = _parse_trends_text(trends_text)
        try:
            generate_daily_batch(store, ManualTrendProvider(trends))
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error))
        return RedirectResponse(url="/", status_code=303)

    @app.post("/api/batches/generate")
    def generate_batch(trends_text: str = Form(default="")) -> dict[str, str | int]:
        trends = _parse_trends_text(trends_text)
        try:
            batch = generate_daily_batch(store, ManualTrendProvider(trends))
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error))
        return {"id": batch.id, "status": batch.status, "target_post_count": batch.target_post_count}

    @app.post("/api/posts/{post_id}/approve")
    def approve_post(post_id: str) -> dict[str, str]:
        return _post_to_response(store, post_id, "approved")

    @app.post("/api/posts/{post_id}/reject")
    def reject_post(post_id: str) -> dict[str, str]:
        return _post_to_response(store, post_id, "rejected")

    @app.post("/api/posts/{post_id}/caption")
    def update_post_caption(post_id: str, update: CaptionUpdate) -> dict[str, str | list[str]]:
        try:
            post = store.set_post_caption(post_id, update.caption)
        except (KeyError, ValueError) as error:
            raise HTTPException(status_code=404 if isinstance(error, KeyError) else 400, detail=str(error))
        return {
            "id": post.id,
            "batch_id": post.batch_id,
            "caption": post.caption,
            "status": post.status,
            "selected_asset_ids": post.selected_asset_ids,
        }

    @app.post("/api/drafts/{draft_id}/approve")
    def approve_draft(draft_id: str) -> dict[str, str]:
        return _legacy_draft_to_response(store, draft_id, "approved")

    @app.post("/api/drafts/{draft_id}/reject")
    def reject_draft(draft_id: str) -> dict[str, str]:
        return _legacy_draft_to_response(store, draft_id, "rejected")

    @app.post("/api/drafts/{draft_id}/caption")
    def update_caption(draft_id: str, update: CaptionUpdate) -> dict[str, str]:
        try:
            draft = store.set_caption(draft_id, update.caption)
        except (KeyError, ValueError) as error:
            raise HTTPException(status_code=404 if isinstance(error, KeyError) else 400, detail=str(error))
        return {
            "id": draft.id,
            "asset_id": draft.asset_id,
            "caption": draft.caption,
            "status": draft.status,
        }

    @app.post("/api/export/approved")
    def export_approved(format: str = "json") -> dict[str, str | int]:
        if format not in {"json", "csv"}:
            raise HTTPException(status_code=400, detail="format must be json or csv")
        result = export_approved_drafts(
            store,
            settings.export_path / f"approved-drafts.{format}",
            format=format,  # type: ignore[arg-type]
        )
        return {"path": str(result.path), "count": result.count, "format": result.format}

    @app.get("/exports/approved.{format}")
    def download_approved_export(format: str) -> FileResponse:
        if format not in {"json", "csv"}:
            raise HTTPException(status_code=400, detail="format must be json or csv")
        result = export_approved_drafts(
            store,
            settings.export_path / f"approved-drafts.{format}",
            format=format,  # type: ignore[arg-type]
        )
        return FileResponse(result.path, filename=result.path.name)

    return app


def _asset_cards(
    store: ContentStore,
    thumbnails: ThumbnailService,
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = [dict(item) for item in store.list_assets()]
    for item in items:
        item["thumbnail_url"] = _thumbnail_url(item, thumbnails)
    return items


def _post_cards(
    store: ContentStore,
    thumbnails: ThumbnailService,
    batch_id: str | None,
) -> list[dict[str, object]]:
    if batch_id is None:
        return []
    posts = store.list_post_draft_cards(batch_id=batch_id)
    for post in posts:
        for asset in post["selected_assets"]:  # type: ignore[index]
            asset["thumbnail_url"] = _thumbnail_url(asset, thumbnails)  # type: ignore[index]
    return posts


def _thumbnail_url(item: Mapping[str, Any], thumbnails: ThumbnailService) -> str:
    asset = MediaAsset(
        id=str(item["asset_id"]),
        filename=str(item["filename"]),
        absolute_path=str(item["absolute_path"]),
        relative_path=str(item["relative_path"]),
        media_type=str(item["media_type"]),
        size_bytes=int(item["size_bytes"]),
        modified_at=0,
    )
    return thumbnails.ensure_thumbnail(asset).relative_url


def _post_to_response(store: ContentStore, post_id: str, status: str) -> dict[str, str]:
    try:
        post = store.set_post_status(post_id, status)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error))
    return {
        "id": post.id,
        "batch_id": post.batch_id,
        "caption": post.caption,
        "status": post.status,
    }


def _legacy_draft_to_response(store: ContentStore, draft_id: str, status: str) -> dict[str, str]:
    try:
        draft = store.set_draft_status(draft_id, status)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error))
    return {
        "id": draft.id,
        "asset_id": draft.asset_id,
        "caption": draft.caption,
        "status": draft.status,
    }


def _parse_trends_text(trends_text: str) -> list[str] | None:
    trends = [line.strip(" -\t") for line in trends_text.splitlines() if line.strip(" -\t")]
    return trends[:6] or None


@lru_cache(maxsize=1)
def get_app() -> FastAPI:
    return create_app()


app = get_app()
