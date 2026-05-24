import csv
import json
from pathlib import Path

from rafa_studio.export import export_approved_drafts
from rafa_studio.models import MediaAsset
from rafa_studio.store import ContentStore


def seed_store(tmp_path: Path) -> ContentStore:
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    approved_path = media_dir / "approved.jpg"
    rejected_path = media_dir / "rejected.jpg"
    approved_path.write_bytes(b"approved")
    rejected_path.write_bytes(b"rejected")

    store = ContentStore(tmp_path / "studio.sqlite3")
    approved_asset = MediaAsset.from_path(approved_path, media_dir)
    rejected_asset = MediaAsset.from_path(rejected_path, media_dir)
    store.upsert_assets([approved_asset, rejected_asset])
    store.set_caption(f"draft-{approved_asset.id}", "Approved Rafa caption")
    store.set_draft_status(f"draft-{approved_asset.id}", "approved")
    store.set_draft_status(f"draft-{rejected_asset.id}", "rejected")
    return store


def test_export_approved_drafts_writes_json(tmp_path: Path):
    store = seed_store(tmp_path)
    output = tmp_path / "approved.json"

    result = export_approved_drafts(store, output, format="json")

    assert result.count == 1
    data = json.loads(output.read_text())
    assert data[0]["filename"] == "approved.jpg"
    assert data[0]["caption"] == "Approved Rafa caption"
    assert data[0]["status"] == "approved"


def test_export_approved_drafts_writes_csv(tmp_path: Path):
    store = seed_store(tmp_path)
    output = tmp_path / "approved.csv"

    result = export_approved_drafts(store, output, format="csv")

    assert result.count == 1
    rows = list(csv.DictReader(output.read_text().splitlines()))
    assert rows[0]["filename"] == "approved.jpg"
    assert rows[0]["caption"] == "Approved Rafa caption"
    assert rows[0]["status"] == "approved"
