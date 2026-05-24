from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from html import escape
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from .models import MediaAsset


@dataclass(frozen=True)
class Thumbnail:
    path: Path
    relative_url: str


class ThumbnailService:
    """Create lightweight local preview files for dashboard review.

    Photos are converted to cached JPEG previews when Pillow can read them.
    Videos use ffmpeg to extract an early frame when ffmpeg is installed and
    the source file is decodable. Anything unsupported falls back to a stable
    SVG placeholder so the dashboard never breaks on HEIC/MOV oddities.
    """

    def __init__(self, cache_dir: str | Path):
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def ensure_thumbnail(self, asset: MediaAsset) -> Thumbnail:
        jpg_path = self.cache_dir / f"{asset.id}.jpg"
        svg_path = self.cache_dir / f"{asset.id}.svg"

        if jpg_path.exists():
            return Thumbnail(path=jpg_path, relative_url=f"/thumbnails/{asset.id}.jpg")

        if asset.media_type == "video":
            if self._try_video_thumbnail(asset, jpg_path):
                svg_path.unlink(missing_ok=True)
                return Thumbnail(path=jpg_path, relative_url=f"/thumbnails/{asset.id}.jpg")
            if svg_path.exists():
                return Thumbnail(path=svg_path, relative_url=f"/thumbnails/{asset.id}.svg")
        elif svg_path.exists():
            return Thumbnail(path=svg_path, relative_url=f"/thumbnails/{asset.id}.svg")

        if asset.media_type == "photo" and self._try_photo_thumbnail(asset, jpg_path):
            return Thumbnail(path=jpg_path, relative_url=f"/thumbnails/{asset.id}.jpg")

        svg_path.write_text(_placeholder_svg(asset), encoding="utf-8")
        return Thumbnail(path=svg_path, relative_url=f"/thumbnails/{asset.id}.svg")

    def _try_photo_thumbnail(self, asset: MediaAsset, output_path: Path) -> bool:
        try:
            with Image.open(asset.absolute_path) as image:
                image = ImageOps.exif_transpose(image)
                image.thumbnail((640, 640))
                if image.mode not in {"RGB", "L"}:
                    image = image.convert("RGB")
                image.save(output_path, format="JPEG", quality=84, optimize=True)
            return True
        except (OSError, UnidentifiedImageError, ValueError):
            output_path.unlink(missing_ok=True)
            return False

    def _try_video_thumbnail(self, asset: MediaAsset, output_path: Path) -> bool:
        if shutil.which("ffmpeg") is None:
            return False
        command = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            "00:00:01",
            "-i",
            asset.absolute_path,
            "-frames:v",
            "1",
            str(output_path),
        ]
        try:
            completed = subprocess.run(command, check=False, capture_output=True, timeout=15)
        except (OSError, subprocess.TimeoutExpired):
            output_path.unlink(missing_ok=True)
            return False
        if completed.returncode != 0 or not output_path.exists():
            output_path.unlink(missing_ok=True)
            return False
        return True


def _placeholder_svg(asset: MediaAsset) -> str:
    label = escape(asset.media_type.upper())
    filename = escape(asset.filename)
    color = "#dbb99e" if asset.media_type == "photo" else "#c1d7c7"
    text_color = "#5f341c" if asset.media_type == "photo" else "#284932"
    return f"""<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"640\" height=\"640\" viewBox=\"0 0 640 640\" role=\"img\" aria-label=\"{filename} {label} preview\">
  <rect width=\"640\" height=\"640\" rx=\"48\" fill=\"{color}\" data-media-type=\"{escape(asset.media_type)}\"/>
  <circle cx=\"500\" cy=\"120\" r=\"72\" fill=\"rgba(255,255,255,0.28)\"/>
  <circle cx=\"164\" cy=\"430\" r=\"112\" fill=\"rgba(255,255,255,0.20)\"/>
  <text x=\"48\" y=\"88\" fill=\"{text_color}\" font-family=\"system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif\" font-size=\"34\" font-weight=\"900\" letter-spacing=\"8\">{label}</text>
  <text x=\"48\" y=\"548\" fill=\"{text_color}\" font-family=\"system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif\" font-size=\"38\" font-weight=\"800\">Rafa</text>
  <text x=\"48\" y=\"594\" fill=\"{text_color}\" font-family=\"system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif\" font-size=\"24\">{filename}</text>
</svg>
"""
