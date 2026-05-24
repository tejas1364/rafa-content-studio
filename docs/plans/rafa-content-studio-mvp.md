# Rafa Content Studio MVP Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a local-first MVP that scans a MacBook iCloud album folder, drafts Rafa captions, and lets Tejas approve or reject content before posting.

**Architecture:** FastAPI serves a lightweight dashboard. A filesystem scanner imports media from a normal folder path, while SQLite stores assets and draft statuses. The MVP avoids Photos private APIs and AirPort SMB complexity.

**Tech Stack:** Python 3.11+, FastAPI, Jinja2, SQLite, pytest, uv.

---

## Acceptance Criteria

- `RAFA_MEDIA_DIR` points at a regular folder containing Rafa photos/videos.
- `/api/scan` imports supported files and creates draft captions.
- `/` shows pending/approved/rejected drafts.
- Draft captions can be edited through API.
- Drafts can be approved or rejected through API.
- `uv run --extra dev pytest -q` passes.

## Follow-up Tasks

### Task 1: Add media thumbnails

Create a static thumbnail cache for supported photos/videos and show previews in the dashboard.

### Task 2: Add batch caption generation profiles

Support caption tones like cute, funny, reflective, chaotic, and product-style Instagram hooks.

### Task 3: Add export queue

Export approved drafts as JSON/CSV for manual upload or later scheduler integration.

### Task 4: Add authentication before network exposure

If hosted beyond localhost, add auth before exposing the approval dashboard.
