from pathlib import Path

from PIL import Image

from rafa_studio.models import MediaAsset
from rafa_studio.thumbnails import ThumbnailService


def test_thumbnail_service_creates_real_preview_for_supported_photo(tmp_path: Path):
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    asset_path = media_dir / "rafa.jpg"
    Image.new("RGB", (80, 60), "red").save(asset_path)
    asset = MediaAsset.from_path(asset_path, media_dir)
    service = ThumbnailService(cache_dir=tmp_path / "cache")

    thumbnail = service.ensure_thumbnail(asset)

    assert thumbnail.relative_url == f"/thumbnails/{asset.id}.jpg"
    assert thumbnail.path.exists()
    with Image.open(thumbnail.path) as image:
        assert image.format == "JPEG"
        assert max(image.size) <= 640


def test_thumbnail_service_creates_placeholder_preview_for_unreadable_photo(tmp_path: Path):
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    asset_path = media_dir / "rafa.jpg"
    asset_path.write_bytes(b"not a real jpg yet")
    asset = MediaAsset.from_path(asset_path, media_dir)
    service = ThumbnailService(cache_dir=tmp_path / "cache")

    thumbnail = service.ensure_thumbnail(asset)

    assert thumbnail.relative_url == f"/thumbnails/{asset.id}.svg"
    assert thumbnail.path.exists()
    assert "rafa.jpg" in thumbnail.path.read_text()
    assert "photo" in thumbnail.path.read_text()


def test_thumbnail_service_uses_svg_fallback_for_video_when_ffmpeg_cannot_decode(tmp_path: Path):
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    asset_path = media_dir / "zoomies.mp4"
    asset_path.write_bytes(b"not a real video yet")
    asset = MediaAsset.from_path(asset_path, media_dir)
    service = ThumbnailService(cache_dir=tmp_path / "cache")

    thumbnail = service.ensure_thumbnail(asset)

    assert thumbnail.relative_url == f"/thumbnails/{asset.id}.svg"
    assert thumbnail.path.exists()
    assert "zoomies.mp4" in thumbnail.path.read_text()
    assert "video" in thumbnail.path.read_text()


def test_thumbnail_service_reuses_existing_preview(tmp_path: Path):
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    asset_path = media_dir / "zoomies.mp4"
    asset_path.write_bytes(b"not a real video yet")
    asset = MediaAsset.from_path(asset_path, media_dir)
    service = ThumbnailService(cache_dir=tmp_path / "cache")

    first = service.ensure_thumbnail(asset)
    first.path.write_text("custom cached preview")
    second = service.ensure_thumbnail(asset)

    assert second.path == first.path
    assert second.path.read_text() == "custom cached preview"
