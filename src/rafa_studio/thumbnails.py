from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path

from .models import MediaAsset


@dataclass(frozen=True)
class Thumbnail:
    path: Path
    relative_url: str


class ThumbnailService:
    """Create lightweight local preview files for dashboard review.

    This MVP intentionally writes SVG placeholders instead of decoding HEIC/MOV files.
    It gives the dashboard stable preview URLs now, while leaving room for real image
    and video frame extraction later.
    """

    def __init__(self, cache_dir: str | Path):
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def ensure_thumbnail(self, asset: MediaAsset) -> Thumbnail:
        path = self.cache_dir / f"{asset.id}.svg"
        if not path.exists():
            path.write_text(_placeholder_svg(asset), encoding="utf-8")
        return Thumbnail(path=path, relative_url=f"/thumbnails/{asset.id}.svg")


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
