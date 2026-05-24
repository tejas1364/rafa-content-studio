from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from .models import ContentBatch, PostDraft, TrendIdea
from .store import ContentStore

DEFAULT_HASHTAGS = ["#rafa", "#dogsoftiktok", "#dogreels", "#puppylife"]
DEFAULT_TRENDS = [
    "POV: tiny dog thinks he owns the house",
    "Weekend photo dump but make it tiny",
    "Suspiciously quiet puppy check",
    "When the zoomies choose you",
    "Tiny dog cinematic universe",
    "Rafa discovers a side quest",
]


class TrendProvider(Protocol):
    def top_trends(self, limit: int = 6) -> list[TrendIdea]:
        """Return structured trend ideas for today's batch."""
        ...


@dataclass(frozen=True)
class ManualTrendProvider:
    """Deterministic MVP provider for pasted or default trend ideas."""

    titles: list[str] | None = None

    def top_trends(self, limit: int = 6) -> list[TrendIdea]:
        titles = self.titles or DEFAULT_TRENDS
        return [
            TrendIdea(
                id=f"trend-{index + 1}",
                title=title,
                platform="instagram" if index < 3 else "instagram,tiktok",
                format_hint="photo post" if index < 3 else "short vertical video",
                caption_angle=_caption_angle(title),
                hashtags=_hashtags_for(title),
            )
            for index, title in enumerate(titles[:limit])
        ]


def generate_daily_batch(
    store: ContentStore,
    trend_provider: TrendProvider | None = None,
) -> ContentBatch:
    """Create exactly six human-reviewable posts: three photos and three videos."""

    trends = (trend_provider or ManualTrendProvider()).top_trends(limit=6)
    if len(trends) < 6:
        raise ValueError("Daily batch generation needs 6 trend ideas")

    assets = store.list_assets()
    photos = [asset for asset in assets if asset["media_type"] == "photo"]
    videos = [asset for asset in assets if asset["media_type"] == "video"]
    if len(photos) < 3 or len(videos) < 3:
        raise ValueError(
            "Daily batch generation needs at least 3 photos and 3 videos "
            f"(found {len(photos)} photos and {len(videos)} videos)"
        )

    created_at = time.time()
    batch = ContentBatch(
        id=f"batch-{int(created_at)}",
        created_at=created_at,
        status="draft",
        target_post_count=6,
    )
    store.create_batch(batch)

    for index, photo_asset in enumerate(photos[:3], start=1):
        trend = trends[index - 1]
        store.add_post_draft(
            PostDraft(
                id=f"{batch.id}-post-{index}",
                batch_id=batch.id,
                post_type="photo",
                platform_targets=["instagram"],
                trend_title=trend.title,
                caption=_caption_for_photo(trend.title),
                hashtags=trend.hashtags,
                selected_asset_ids=[str(photo_asset["asset_id"])],
                overlay_text=_overlay_for(trend.title),
                edit_notes=(
                    "Use as an Instagram picture post. Keep the image uncropped if possible, "
                    "and make Rafa's face or expression the first visual read."
                ),
            )
        )

    for offset, video_asset in enumerate(videos[:3], start=1):
        index = offset + 3
        trend = trends[index - 1]
        store.add_post_draft(
            PostDraft(
                id=f"{batch.id}-post-{index}",
                batch_id=batch.id,
                post_type="video",
                platform_targets=["instagram", "tiktok"],
                trend_title=trend.title,
                caption=_caption_for_video(trend.title),
                hashtags=trend.hashtags,
                selected_asset_ids=[str(video_asset["asset_id"])],
                overlay_text=_overlay_for(trend.title),
                edit_notes=(
                    "Use this as a short vertical Reel/TikTok. Trim to the strongest 7-12 seconds, "
                    "keep Rafa visible early, and pair with a current playful sound."
                ),
            )
        )

    return batch


def _caption_angle(title: str) -> str:
    lowered = title.lower()
    if "pov" in lowered:
        return "Rafa as tiny main character with a very large sense of authority"
    if "zoom" in lowered:
        return "high-energy puppy chaos"
    if "quiet" in lowered or "suspicious" in lowered:
        return "the suspicious silence every dog owner recognizes"
    if "photo" in lowered or "dump" in lowered:
        return "soft photo-post storytelling from Rafa's day"
    return "playful tiny-dog story with a simple hook"


def _hashtags_for(title: str) -> list[str]:
    tags = list(DEFAULT_HASHTAGS)
    lowered = title.lower()
    if "pov" in lowered:
        tags.append("#pov")
    if "zoom" in lowered:
        tags.append("#zoomies")
    if "photo" in lowered or "dump" in lowered:
        tags.append("#photodump")
    if "side quest" in lowered:
        tags.append("#sidequest")
    return tags


def _caption_for_photo(title: str) -> str:
    return f"{title}. Rafa had one job: be tiny and somehow still run the whole frame."


def _caption_for_video(title: str) -> str:
    return f"{title}. Rafa understood the assignment and then rewrote it in his favor."


def _overlay_for(title: str) -> list[str]:
    if "POV" in title.upper():
        return ["POV: Rafa runs the house", "daily inspection complete"]
    if "zoom" in title.lower():
        return ["the zoomies have selected a target", "no furniture was consulted"]
    if "quiet" in title.lower() or "suspicious" in title.lower():
        return ["it got quiet", "Rafa was absolutely involved"]
    return [title, "Rafa edition"]
