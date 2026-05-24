from pathlib import Path

from rafa_studio.batch import ManualTrendProvider, generate_daily_batch
from rafa_studio.export import export_draft_folders
from rafa_studio.ingest import scan_media_directory
from rafa_studio.models import MediaAsset
from rafa_studio.pipeline import run_daily
from rafa_studio.store import ContentStore


def make_asset(media_dir: Path, filename: str, payload: bytes = b"media") -> MediaAsset:
    path = media_dir / filename
    path.write_bytes(payload)
    return MediaAsset.from_path(path, media_dir)


def seed_media(media_dir: Path) -> None:
    media_dir.mkdir()
    for filename in [
        "photo-one.jpg",
        "photo-two.png",
        "photo-three.jpeg",
        "zoomies.mov",
        "landlord.mp4",
        "side-eye.m4v",
    ]:
        (media_dir / filename).write_bytes(filename.encode())


def test_generate_daily_batch_creates_three_photo_posts_and_three_video_posts(tmp_path: Path):
    media_dir = tmp_path / "media"
    seed_media(media_dir)
    store = ContentStore(tmp_path / "studio.sqlite3")
    store.upsert_assets([MediaAsset.from_path(path, media_dir) for path in media_dir.iterdir()])
    trends = ManualTrendProvider(["photo one", "photo two", "photo three", "video one", "video two", "video three"])

    batch = generate_daily_batch(store, trends)
    posts = store.list_post_drafts(batch.id)

    assert batch.target_post_count == 6
    assert len(posts) == 6
    assert [post.post_type for post in posts].count("photo") == 3
    assert [post.post_type for post in posts].count("video") == 3
    assert all(len(post.selected_asset_ids) == 1 for post in posts)
    assert [post.trend_title for post in posts] == [
        "photo one",
        "photo two",
        "photo three",
        "video one",
        "video two",
        "video three",
    ]


def test_export_draft_folders_writes_reviewable_post_directories(tmp_path: Path):
    media_dir = tmp_path / "media"
    seed_media(media_dir)
    store = ContentStore(tmp_path / "studio.sqlite3")
    store.upsert_assets([MediaAsset.from_path(path, media_dir) for path in media_dir.iterdir()])
    batch = generate_daily_batch(
        store,
        ManualTrendProvider(["photo one", "photo two", "photo three", "video one", "video two", "video three"]),
    )

    result = export_draft_folders(store, batch.id, tmp_path / "drafts")

    assert result.count == 6
    assert result.path.exists()
    assert (result.path / "run-summary.md").exists()
    assert (result.path / "trend-research.json").exists()
    post_dirs = sorted(path for path in result.path.iterdir() if path.is_dir())
    assert [path.name for path in post_dirs] == [
        "01-instagram-photo",
        "02-instagram-photo",
        "03-instagram-photo",
        "04-reel-tiktok",
        "05-reel-tiktok",
        "06-reel-tiktok",
    ]
    for post_dir in post_dirs:
        assert (post_dir / "caption.md").read_text(encoding="utf-8").strip()
        assert (post_dir / "hashtags.txt").read_text(encoding="utf-8").strip()
        assert (post_dir / "post.json").exists()
        assert any((post_dir / "media").iterdir())


def test_run_daily_scans_generates_and_exports_draft_folder(tmp_path: Path):
    media_dir = tmp_path / "media"
    seed_media(media_dir)
    store = ContentStore(tmp_path / "studio.sqlite3")

    result = run_daily(
        store=store,
        media_dir=media_dir,
        output_dir=tmp_path / "daily-drafts",
        trend_titles=["photo one", "photo two", "photo three", "video one", "video two", "video three"],
    )

    assert result.assets_imported == 6
    assert result.post_count == 6
    assert result.output_path.exists()
    assert len(store.list_assets()) == 6
    assert len(store.list_post_drafts(result.batch_id)) == 6
