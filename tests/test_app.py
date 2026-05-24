from pathlib import Path

from fastapi.testclient import TestClient

from rafa_studio.app import create_app
from rafa_studio.config import StudioSettings
from rafa_studio.store import ContentStore


def make_client(tmp_path: Path) -> tuple[TestClient, ContentStore]:
    media_dir = tmp_path / "icloud-rafa-album"
    media_dir.mkdir()
    for filename in [
        "zoomies.mov",
        "tiny-landlord.mp4",
        "side-eye.m4v",
        "cute.jpg",
        "nap.png",
        "walk.jpeg",
    ]:
        (media_dir / filename).write_bytes(filename.encode())
    db_path = tmp_path / "studio.sqlite3"
    settings = StudioSettings(media_dir=str(media_dir), database_path=str(db_path))
    store = ContentStore(db_path)
    app = create_app(settings=settings, store=store)
    return TestClient(app), store


def test_dashboard_shows_media_library_without_creating_drafts_on_scan(tmp_path: Path):
    client, store = make_client(tmp_path)

    response = client.post("/api/scan")
    assert response.status_code == 200
    assert response.json()["assets_imported"] == 6

    response = client.get("/")

    assert response.status_code == 200
    assert "cute.jpg" in response.text
    assert "Media library" in response.text
    assert "No post drafts yet" in response.text
    assert store.list_drafts() == []


def test_generate_batch_endpoint_creates_reviewable_post_drafts(tmp_path: Path):
    client, store = make_client(tmp_path)
    client.post("/api/scan")

    response = client.post("/api/batches/generate")

    assert response.status_code == 200
    assert response.json()["target_post_count"] == 4
    posts = store.list_post_drafts(response.json()["id"])
    assert len(posts) == 4
    assert [post.post_type for post in posts].count("video") == 3
    assert [post.post_type for post in posts].count("slideshow") == 1


def test_generate_batch_accepts_researched_trends_from_dashboard_form(tmp_path: Path):
    client, store = make_client(tmp_path)
    client.post("/api/scan")

    response = client.post(
        "/api/batches/generate",
        data={
            "trends_text": "\n".join(
                [
                    "Tiny dog landlord inspection",
                    "Zoomies chose violence today",
                    "Quiet puppy suspicious activity",
                    "Sunday Rafa photo dump",
                ]
            )
        },
    )

    assert response.status_code == 200
    posts = store.list_post_drafts(response.json()["id"])
    assert [post.trend_title for post in posts] == [
        "Tiny dog landlord inspection",
        "Zoomies chose violence today",
        "Quiet puppy suspicious activity",
        "Sunday Rafa photo dump",
    ]


def test_can_approve_and_reject_post_drafts(tmp_path: Path):
    client, store = make_client(tmp_path)
    client.post("/api/scan")
    batch_id = client.post("/api/batches/generate").json()["id"]
    draft = store.list_post_drafts(batch_id)[0]

    approved = client.post(f"/api/posts/{draft.id}/approve")
    rejected = client.post(f"/api/posts/{draft.id}/reject")

    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert store.get_post_draft(draft.id).status == "rejected"


def test_can_edit_post_caption_before_approval(tmp_path: Path):
    client, store = make_client(tmp_path)
    client.post("/api/scan")
    batch_id = client.post("/api/batches/generate").json()["id"]
    draft = store.list_post_drafts(batch_id)[0]

    response = client.post(
        f"/api/posts/{draft.id}/caption",
        json={"caption": "Rafa discovered the ancient art of strategic napping."},
    )

    assert response.status_code == 200
    assert response.json()["caption"] == "Rafa discovered the ancient art of strategic napping."
    assert store.get_post_draft(draft.id).caption == "Rafa discovered the ancient art of strategic napping."
