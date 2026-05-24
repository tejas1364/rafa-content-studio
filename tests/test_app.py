from pathlib import Path

from fastapi.testclient import TestClient

from rafa_studio.app import create_app
from rafa_studio.config import StudioSettings
from rafa_studio.store import ContentStore


def make_client(tmp_path: Path) -> tuple[TestClient, ContentStore]:
    media_dir = tmp_path / "icloud-rafa-album"
    media_dir.mkdir()
    (media_dir / "cute.jpg").write_bytes(b"jpg")
    db_path = tmp_path / "studio.sqlite3"
    settings = StudioSettings(media_dir=str(media_dir), database_path=str(db_path))
    store = ContentStore(db_path)
    app = create_app(settings=settings, store=store)
    return TestClient(app), store


def test_dashboard_shows_assets_and_generated_drafts(tmp_path: Path):
    client, _store = make_client(tmp_path)

    response = client.post("/api/scan")
    assert response.status_code == 200
    assert response.json()["assets_imported"] == 1

    response = client.get("/")

    assert response.status_code == 200
    assert "cute.jpg" in response.text
    assert "Rafa" in response.text
    assert "Pending" in response.text


def test_can_approve_and_reject_drafts(tmp_path: Path):
    client, store = make_client(tmp_path)
    client.post("/api/scan")
    draft = store.list_drafts()[0]

    approved = client.post(f"/api/drafts/{draft.id}/approve")
    rejected = client.post(f"/api/drafts/{draft.id}/reject")

    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert store.get_draft(draft.id).status == "rejected"


def test_can_edit_caption_before_approval(tmp_path: Path):
    client, store = make_client(tmp_path)
    client.post("/api/scan")
    draft = store.list_drafts()[0]

    response = client.post(
        f"/api/drafts/{draft.id}/caption",
        json={"caption": "Rafa discovered the ancient art of strategic napping."},
    )

    assert response.status_code == 200
    assert response.json()["caption"] == "Rafa discovered the ancient art of strategic napping."
    assert store.get_draft(draft.id).caption == "Rafa discovered the ancient art of strategic napping."
