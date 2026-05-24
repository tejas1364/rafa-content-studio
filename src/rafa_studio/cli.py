from __future__ import annotations

import argparse
from pathlib import Path

from .batch import ManualTrendProvider, generate_daily_batch
from .config import StudioSettings
from .export import export_approved_drafts, export_draft_folders
from .ingest import scan_media_directory
from .pipeline import run_daily
from .store import ContentStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rafa-studio")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Import media from RAFA_MEDIA_DIR")
    scan_parser.add_argument("--media-dir", help="Override the configured media directory")

    generate_parser = subparsers.add_parser(
        "generate-batch",
        help="Generate exactly 6 post drafts: 3 photos and 3 videos",
    )
    _add_trend_args(generate_parser)

    daily_parser = subparsers.add_parser(
        "run-daily",
        help="Scan media, generate 6 draft posts, and export a dated draft folder",
    )
    daily_parser.add_argument("--media-dir", help="Override the configured media directory")
    daily_parser.add_argument("--output-dir", help="Override the draft folder output directory")
    _add_trend_args(daily_parser)

    export_parser = subparsers.add_parser("export-approved", help="Export approved post drafts")
    export_parser.add_argument("--format", choices=["json", "csv"], default="json")
    export_parser.add_argument("--output", help="Output file path")

    export_batch_parser = subparsers.add_parser(
        "export-draft-folders",
        help="Export the latest or selected batch as reviewable post folders",
    )
    export_batch_parser.add_argument("--batch-id", help="Batch ID to export. Defaults to latest batch.")
    export_batch_parser.add_argument("--output-dir", help="Output directory for dated draft folders")

    args = parser.parse_args(argv)
    settings = StudioSettings()
    store = ContentStore(settings.db_path)

    if args.command == "scan":
        media_dir = Path(args.media_dir).expanduser() if args.media_dir else settings.media_path
        imported = store.upsert_assets(scan_media_directory(media_dir))
        print(f"Imported {imported} assets from {media_dir}")
        return 0

    if args.command == "generate-batch":
        trends = _trend_titles_from_args(args)
        batch = generate_daily_batch(store, ManualTrendProvider(trends))
        print(f"Generated {batch.id} with {batch.target_post_count} post drafts")
        return 0

    if args.command == "run-daily":
        media_dir = Path(args.media_dir).expanduser() if args.media_dir else settings.media_path
        output_dir = Path(args.output_dir).expanduser() if args.output_dir else settings.export_path / "drafts"
        result = run_daily(
            store=store,
            media_dir=media_dir,
            output_dir=output_dir,
            trend_titles=_trend_titles_from_args(args),
        )
        print(f"Imported {result.assets_imported} assets from {media_dir}")
        print(f"Generated {result.batch_id} with {result.post_count} draft posts")
        print(f"Draft folder: {result.output_path}")
        return 0

    if args.command == "export-approved":
        output = Path(args.output).expanduser() if args.output else settings.export_path / f"approved-drafts.{args.format}"
        result = export_approved_drafts(store, output, format=args.format)
        print(f"Exported {result.count} approved post drafts to {result.path}")
        return 0

    if args.command == "export-draft-folders":
        batch_id = args.batch_id
        if not batch_id:
            latest = store.latest_batch()
            if latest is None:
                raise SystemExit("No batch exists yet. Run generate-batch or run-daily first.")
            batch_id = latest.id
        output_dir = Path(args.output_dir).expanduser() if args.output_dir else settings.export_path / "drafts"
        result = export_draft_folders(store, batch_id, output_dir)
        print(f"Exported {result.count} draft post folders to {result.path}")
        return 0

    return 1


def _add_trend_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--trend",
        action="append",
        dest="trends",
        help="Trend idea to use. Pass six times to override the MVP defaults.",
    )
    parser.add_argument(
        "--trends-file",
        help="Plain text file with researched trend ideas, one per line.",
    )


def _trend_titles_from_args(args: argparse.Namespace) -> list[str] | None:
    trends = args.trends
    if args.trends_file:
        trends_path = Path(args.trends_file).expanduser()
        trends = [
            line.strip(" -\t")
            for line in trends_path.read_text(encoding="utf-8").splitlines()
            if line.strip(" -\t")
        ]
    return trends


if __name__ == "__main__":
    raise SystemExit(main())
