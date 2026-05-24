from pathlib import Path

from rafa_studio.batch import ManualTrendProvider, generate_daily_batch
from rafa_studio.models import MediaAsset
from rafa_studio.store import ContentStore


def make_asset(media_dir: Path, filename: str, payload: bytes = b"media") -> MediaAsset:
    path = media_dir / filename
    path.write_bytes(payload)
    return MediaAsset.from_path(path, media_dir)


def seed_assets(tmp_path: Path) -> tuple[ContentStore, list[MediaAsset]]:
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    assets = [
        make_asset(media_dir, "nap-1.jpg"),
        make_asset(media_dir, "nap-2.png"),
        make_asset(media_dir, "nap-3.jpeg"),
        make_asset(media_dir, "zoomies.mov"),
        make_asset(media_dir, "tiny-landlord.mp4"),
        make_asset(media_dir, "side-eye.m4v"),
    ]
    store = ContentStore(tmp_path / "studio.sqlite3")
    store.upsert_assets(assets)
    return store, assets


def test_scanning_assets_does_not_create_one_draft_per_media_file(tmp_path: Path):
    store, assets = seed_assets(tmp_path)

    assert len(store.list_assets_with_drafts()) == len(assets)
    assert store.list_drafts() == []


def test_generate_daily_batch_creates_exactly_three_photos_and_three_videos(tmp_path: Path):
    store, _assets = seed_assets(tmp_path)
    trends = ManualTrendProvider(
        [
            "POV: tiny dog thinks he owns the house",
            "When the zoomies choose you",
            "Suspiciously quiet puppy check",
            "Weekend photo dump but make it tiny",
            "Tiny dog cinematic universe",
            "Rafa discovers a side quest",
        ]
    )

    batch = generate_daily_batch(store, trends)
    posts = store.list_post_drafts(batch.id)

    assert batch.target_post_count == 6
    assert len(posts) == 6
    assert [post.post_type for post in posts].count("photo") == 3
    assert [post.post_type for post in posts].count("video") == 3
    assert all(post.status == "pending" for post in posts)
    assert all(post.caption for post in posts)
    assert all(post.hashtags for post in posts)

    video_posts = [post for post in posts if post.post_type == "video"]
    assert all(len(post.selected_asset_ids) == 1 for post in video_posts)

    photo_posts = [post for post in posts if post.post_type == "photo"]
    assert all(len(post.selected_asset_ids) == 1 for post in photo_posts)


def test_generate_daily_batch_refuses_when_required_media_is_missing(tmp_path: Path):
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    store = ContentStore(tmp_path / "studio.sqlite3")
    store.upsert_assets(
        [
            make_asset(media_dir, "one-video.mov"),
            make_asset(media_dir, "one-photo.jpg"),
            make_asset(media_dir, "two-photo.jpg"),
        ]
    )

    trends = ManualTrendProvider(["one", "two", "three", "four", "five", "six"])

    try:
        generate_daily_batch(store, trends)
    except ValueError as error:
        assert "3 videos" in str(error)
        assert "3 photos" in str(error)
    else:
        raise AssertionError("Expected missing media to prevent batch generation")
