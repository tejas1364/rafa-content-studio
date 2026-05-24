from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from .models import ContentBatch, PostDraft, TrendIdea
from .store import ContentStore

DEFAULT_HASHTAGS = ["#rafa", "#dogsoftiktok", "#dogreels", "#puppylife"]


class TrendProvider(Protocol):
    def top_trends(self, limit: int = 4) -> list[TrendIdea]:
        """Return structured trend ideas for today's batch."""
        ...


@dataclass(frozen=True)
class ManualTrendProvider:
    """Deterministic MVP provider for pasted or default trend ideas."""

    titles: list[str] | None = None

    def top_trends(self, limit: int = 4) -> list[TrendIdea]:
        titles = self.titles or [
            "POV: tiny dog thinks he owns the house",
            "When the zoomies choose you",
            "Suspiciously quiet puppy check",
            "Weekend photo dump but make it tiny",
        ]
        return [
            TrendIdea(
                id=f"trend-{index + 1}",
                title=title,
                platform="instagram,tiktok",
                format_hint="slideshow" if index == 3 else "short vertical video",
                caption_angle=_caption_angle(title),
                hashtags=_hashtags_for(title),
            )
            for index, title in enumerate(titles[:limit])
        ]


def generate_daily_batch(
    store: ContentStore,
    trend_provider: TrendProvider | None = None,
) -> ContentBatch:
    """Create exactly four human-reviewable posts: three videos and one slideshow."""

    trends = (trend_provider or ManualTrendProvider()).top_trends(limit=4)
    if len(trends) < 4:
        raise ValueError("Daily batch generation needs 4 trend ideas")

    assets = store.list_assets()
    videos = [asset for asset in assets if asset["media_type"] == "video"]
    photos = [asset for asset in assets if asset["media_type"] == "photo"]
    if len(videos) < 3 or len(photos) < 3:
        raise ValueError(
            "Daily batch generation needs at least 3 videos and 3 photos "
            f"(found {len(videos)} videos and {len(photos)} photos)"
        )

    created_at = time.time()
    batch = ContentBatch(
        id=f"batch-{int(created_at)}",
        created_at=created_at,
        status="draft",
        target_post_count=4,
    )
    store.create_batch(batch)

    for index, video_asset in enumerate(videos[:3], start=1):
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
                    "Use this as a short vertical reel. Trim to the strongest 7-12 seconds, "
                    "keep Rafa visible early, and pair with a current upbeat or playful sound."
                ),
            )
        )

    slideshow_trend = trends[3]
    store.add_post_draft(
        PostDraft(
            id=f"{batch.id}-post-4",
            batch_id=batch.id,
            post_type="slideshow",
            platform_targets=["instagram", "tiktok"],
            trend_title=slideshow_trend.title,
            caption=_caption_for_slideshow(slideshow_trend.title),
            hashtags=slideshow_trend.hashtags,
            selected_asset_ids=[str(asset["asset_id"]) for asset in photos[:3]],
            overlay_text=["Rafa photo dump", "tiny moments", "main character archive"],
            edit_notes="Use 3-8 photos as a carousel/slideshow. Keep the cutest face-forward image first.",
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
    return "soft photo-dump storytelling from Rafa's day"


def _hashtags_for(title: str) -> list[str]:
    tags = list(DEFAULT_HASHTAGS)
    lowered = title.lower()
    if "pov" in lowered:
        tags.append("#pov")
    if "zoom" in lowered:
        tags.append("#zoomies")
    if "photo" in lowered or "dump" in lowered:
        tags.append("#photodump")
    return tags


def _caption_for_video(title: str) -> str:
    return f"{title}. Rafa understood the assignment and then rewrote it in his favor."


def _caption_for_slideshow(title: str) -> str:
    return f"{title}. A tiny archive of Rafa moments that felt too important not to post."


def _overlay_for(title: str) -> list[str]:
    if "POV" in title.upper():
        return ["POV: Rafa runs the house", "daily inspection complete"]
    if "zoom" in title.lower():
        return ["the zoomies have selected a target", "no furniture was consulted"]
    if "quiet" in title.lower() or "suspicious" in title.lower():
        return ["it got quiet", "Rafa was absolutely involved"]
    return [title, "Rafa edition"]
