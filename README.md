# Rafa Content Studio

Local-first MVP for turning a Rafa iCloud album folder into reviewable content drafts.

## What this MVP does

- Scans a local folder that represents the Rafa iCloud album on the MacBook.
- Imports supported media files: `.jpg`, `.jpeg`, `.png`, `.heic`, `.webp`, `.mov`, `.mp4`, `.m4v`.
- Maintains a media library without creating one fake draft per file.
- Generates one daily review batch with exactly 4 complete post drafts: 3 video posts and 1 slideshow post.
- Uses structured MVP trend ideas now, with a manual trend-input path ready for research-driven ideas next.
- Provides a browser dashboard to approve, reject, or inspect post drafts.
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

## Generate today's batch

After scanning, generate the four-post daily batch from the dashboard with **Generate Today's Batch**.

From the CLI:

```bash
rafa-studio scan
rafa-studio generate-batch
```

To pass manually researched trend ideas into the MVP generator:

```bash
rafa-studio generate-batch \
  --trend "POV: tiny dog thinks he owns the house" \
  --trend "When the zoomies choose you" \
  --trend "Suspiciously quiet puppy check" \
  --trend "Weekend photo dump but make it tiny"
```

The generator requires at least 3 videos and 3 photos. It creates exactly 3 video posts and 1 slideshow post for human approval.

## Export approved drafts

From the dashboard, use **Export JSON** or **Export CSV** after approving post drafts.

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
