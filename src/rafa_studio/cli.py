from __future__ import annotations

import argparse
from pathlib import Path

from .batch import ManualTrendProvider, generate_daily_batch
from .config import StudioSettings
from .export import export_approved_drafts
from .ingest import scan_media_directory
from .store import ContentStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rafa-studio")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Import media from RAFA_MEDIA_DIR")
    scan_parser.add_argument("--media-dir", help="Override the configured media directory")

    generate_parser = subparsers.add_parser(
        "generate-batch",
        help="Generate exactly 4 post drafts: 3 videos and 1 slideshow",
    )
    generate_parser.add_argument(
        "--trend",
        action="append",
        dest="trends",
        help="Trend idea to use. Pass four times to override the MVP defaults.",
    )

    export_parser = subparsers.add_parser("export-approved", help="Export approved post drafts")
    export_parser.add_argument("--format", choices=["json", "csv"], default="json")
    export_parser.add_argument("--output", help="Output file path")

    args = parser.parse_args(argv)
    settings = StudioSettings()
    store = ContentStore(settings.db_path)

    if args.command == "scan":
        media_dir = Path(args.media_dir).expanduser() if args.media_dir else settings.media_path
        imported = store.upsert_assets(scan_media_directory(media_dir))
        print(f"Imported {imported} assets from {media_dir}")
        return 0

    if args.command == "generate-batch":
        batch = generate_daily_batch(store, ManualTrendProvider(args.trends))
        print(f"Generated {batch.id} with {batch.target_post_count} post drafts")
        return 0

    if args.command == "export-approved":
        output = Path(args.output).expanduser() if args.output else settings.export_path / f"approved-drafts.{args.format}"
        result = export_approved_drafts(store, output, format=args.format)
        print(f"Exported {result.count} approved post drafts to {result.path}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
