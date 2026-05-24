from pathlib import Path

from rafa_studio.config import StudioSettings
from rafa_studio.ingest import scan_media_directory
from rafa_studio.models import MediaAsset


def test_scan_media_directory_finds_supported_media_and_ignores_noise(tmp_path: Path):
    album = tmp_path / "Rafa Album"
    nested = album / "Favorites"
    nested.mkdir(parents=True)
    photo = nested / "rafa-nap.JPG"
    video = album / "zoomies.mp4"
    noise = album / ".DS_Store"
    photo.write_bytes(b"fake image")
    video.write_bytes(b"fake video")
    noise.write_text("mac metadata")

    assets = scan_media_directory(album)

    assert [asset.filename for asset in assets] == ["rafa-nap.JPG", "zoomies.mp4"]
    assert assets[0].media_type == "photo"
    assert assets[1].media_type == "video"
    assert assets[0].relative_path == "Favorites/rafa-nap.JPG"


def test_scan_media_directory_returns_empty_list_when_album_missing(tmp_path: Path):
    missing_album = tmp_path / "Not Exported Yet"

    assert scan_media_directory(missing_album) == []


def test_media_asset_id_is_stable_for_same_file(tmp_path: Path):
    media_path = tmp_path / "rafa.jpg"
    media_path.write_bytes(b"same rafa")

    first = MediaAsset.from_path(media_path, tmp_path)
    second = MediaAsset.from_path(media_path, tmp_path)

    assert first.id == second.id
    assert first.relative_path == "rafa.jpg"


def test_settings_default_to_icloud_album_style_path():
    settings = StudioSettings()

    assert "Pictures" in settings.media_dir
    assert "Rafa" in settings.media_dir
