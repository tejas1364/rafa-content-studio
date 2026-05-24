# Rafa Content Studio

Local-first MVP for turning a Rafa iCloud album folder into reviewable daily content draft folders.

## What this MVP does

- Scans a local folder that represents the Rafa iCloud album on the MacBook.
- Imports supported media files: `.jpg`, `.jpeg`, `.png`, `.heic`, `.webp`, `.mov`, `.mp4`, `.m4v`.
- Maintains a media library without creating one fake draft per file.
- Generates one daily review batch with exactly 6 complete post drafts: 3 Instagram photo posts and 3 Reels/TikToks.
- Uses structured MVP trend ideas now, with a manual trend-input path ready for OpenAI/ChatGPT trend research next.
- Exports a dated draft folder with one subfolder per post, copied media, captions, hashtags, edit notes, and JSON metadata.
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

After scanning, generate the six-post daily batch from the dashboard with **Generate Today's Batch**.

From the CLI:

```bash
rafa-studio scan
rafa-studio generate-batch
```

To pass manually researched trend ideas into the MVP generator:

```bash
rafa-studio generate-batch \
  --trend "POV: tiny dog thinks he owns the house" \
  --trend "Weekend photo dump but make it tiny" \
  --trend "Suspiciously quiet puppy check" \
  --trend "When the zoomies choose you" \
  --trend "Tiny dog cinematic universe" \
  --trend "Rafa discovers a side quest"
```

Or save researched ideas in a text file, one per line:

```bash
rafa-studio generate-batch --trends-file today-trends.txt
```

The dashboard also has a text area for pasting six researched trend ideas before generation.

The generator requires at least 3 photos and 3 videos. It creates exactly 3 Instagram photo posts and 3 Reels/TikToks for human approval.

## Run the daily draft folder pipeline

`run-daily` scans the media folder, generates the six-post batch, and exports a dated folder under `$RAFA_EXPORT_DIR/drafts`.

```bash
rafa-studio run-daily
```

With explicit paths:

```bash
rafa-studio run-daily \
  --media-dir "$HOME/Pictures/Rafa iCloud Album" \
  --output-dir "$HOME/.rafa-content-studio/drafts" \
  --trends-file today-trends.txt
```

Example output shape:

```text
~/.rafa-content-studio/drafts/2026-05-24/
  run-summary.md
  trend-research.json
  01-instagram-photo/
    media/
    caption.md
    hashtags.txt
    edit_notes.md
    post.json
  04-reel-tiktok/
    media/
    caption.md
    hashtags.txt
    edit_notes.md
    post.json
```

For video drafts, the exporter tries to create a short vertical `draft.mp4` with `ffmpeg`. If ffmpeg cannot decode the source yet, it copies the source video into the draft folder and keeps the edit notes. Practical, if not yet cinematic.

## Export approved drafts

From the dashboard, use **Export JSON** or **Export CSV** after approving post drafts.

From the CLI:

```bash
rafa-studio export-approved --format json
rafa-studio export-approved --format csv
```

To export review folders for the latest batch:

```bash
rafa-studio export-draft-folders
```

## Test

```bash
uv run --extra dev pytest -q
```

## MVP boundaries

This version does not auto-post to Instagram or TikTok. It creates the approval workflow first so the content queue can be trusted before automation touches external accounts. Sensible, if a little less flashy.
