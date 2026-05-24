import csv
import json
from pathlib import Path

from rafa_studio.batch import ManualTrendProvider, generate_daily_batch
from rafa_studio.export import export_approved_drafts
from rafa_studio.models import MediaAsset
from rafa_studio.store import ContentStore


def seed_store(tmp_path: Path) -> ContentStore:
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    for filename in [
        "one.mov",
        "two.mp4",
        "three.m4v",
        "slide-one.jpg",
        "slide-two.jpg",
        "slide-three.jpg",
    ]:
        path = media_dir / filename
        path.write_bytes(filename.encode())

    store = ContentStore(tmp_path / "studio.sqlite3")
    store.upsert_assets([MediaAsset.from_path(path, media_dir) for path in media_dir.iterdir()])
    batch = generate_daily_batch(
        store,
        ManualTrendProvider(["one", "two", "three", "slideshow"]),
    )
    posts = store.list_post_drafts(batch.id)
    store.set_post_caption(posts[0].id, "Approved Rafa caption")
    store.set_post_status(posts[0].id, "approved")
    store.set_post_status(posts[1].id, "rejected")
    return store


def test_export_approved_drafts_writes_json(tmp_path: Path):
    store = seed_store(tmp_path)
    output = tmp_path / "approved.json"

    result = export_approved_drafts(store, output, format="json")

    assert result.count == 1
    data = json.loads(output.read_text())
    assert data[0]["post_type"] == "video"
    assert data[0]["caption"] == "Approved Rafa caption"
    assert data[0]["status"] == "approved"


def test_export_approved_drafts_writes_csv(tmp_path: Path):
    store = seed_store(tmp_path)
    output = tmp_path / "approved.csv"

    result = export_approved_drafts(store, output, format="csv")

    assert result.count == 1
    rows = list(csv.DictReader(output.read_text().splitlines()))
    assert rows[0]["post_type"] == "video"
    assert rows[0]["caption"] == "Approved Rafa caption"
    assert rows[0]["status"] == "approved"
