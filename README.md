# Rafa Content Studio

Local-first MVP for turning a Rafa iCloud album folder into reviewable content drafts.

## What this MVP does

- Scans a local folder that represents the Rafa iCloud album on the MacBook.
- Imports supported media files: `.jpg`, `.jpeg`, `.png`, `.heic`, `.webp`, `.mov`, `.mp4`, `.m4v`.
- Creates one pending draft caption per imported asset.
- Provides a browser dashboard to approve, reject, or inspect drafts.
- Stores state locally in SQLite.

## Run locally

### Option A: with uv

```bash
cd /home/tejas/workspace/rafa-content-studio
uv run --extra dev uvicorn rafa_studio.app:app --reload
```

### Option B: with standard Python venv

```bash
cd /home/tejas/workspace/rafa-content-studio
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
uvicorn rafa_studio.app:app --reload
```

Open http://127.0.0.1:8000.

## Point it at the MacBook iCloud album folder

Set `RAFA_MEDIA_DIR` to the album directory before starting the app:

```bash
export RAFA_MEDIA_DIR="$HOME/Pictures/Rafa iCloud Album"
uv run --extra dev uvicorn rafa_studio.app:app --reload
```

If the iCloud album is visible through Photos but not as normal files, export/sync the album into a regular folder for the MVP. The app intentionally watches a normal filesystem path so it does not need Apple Photos private database access.

## Optional database and output locations

```bash
export RAFA_STUDIO_DB="$HOME/.rafa-content-studio/studio.sqlite3"
export RAFA_THUMBNAIL_DIR="$HOME/.rafa-content-studio/thumbnails"
export RAFA_EXPORT_DIR="$HOME/.rafa-content-studio/exports"
```

## Export approved drafts

From the dashboard, use **Export JSON** or **Export CSV** after approving drafts.

From the CLI:

```bash
rafa-studio export-approved --format json
rafa-studio export-approved --format csv
```

## Test

```bash
uv run --extra dev pytest -q
```

## MVP boundaries

This version does not auto-post to Instagram or TikTok. It creates the approval workflow first so the content queue can be trusted before automation touches external accounts. Sensible, if a little less flashy.
