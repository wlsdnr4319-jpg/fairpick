"""북마크 (레퍼런스 13장: 같은 박람회를 두 번 북마크해도 1건)."""

from tests import factories as f


def test_bookmark_is_idempotent(db, client):
    user = f.user(db)
    fair = f.fair(db, category=f.category(db), venue=f.venue(db))
    h = f.auth_header(user)

    for _ in range(2):
        res = client.put(f"/api/v1/fairs/{fair.id}/bookmark", headers=h)
        assert res.status_code == 200
        assert res.json() == {"fair_id": fair.id, "bookmarked": True, "bookmark_count": 1}

    assert client.get(f"/api/v1/fairs/{fair.id}", headers=h).json()["is_bookmarked"] is True
    assert client.get(f"/api/v1/fairs/{fair.id}").json()["is_bookmarked"] is False
    item = client.get("/api/v1/fairs", headers=h).json()["items"][0]
    assert item["is_bookmarked"] is True

    mine = client.get("/api/v1/me/bookmarks", headers=h).json()
    assert mine["total"] == 1 and mine["items"][0]["id"] == fair.id

    for _ in range(2):
        res = client.delete(f"/api/v1/fairs/{fair.id}/bookmark", headers=h)
        assert res.json() == {"fair_id": fair.id, "bookmarked": False, "bookmark_count": 0}


def test_bookmark_requires_login_and_published_fair(db, client):
    hidden = f.fair(db, category=f.category(db), venue=f.venue(db), status="hidden")
    assert client.put(f"/api/v1/fairs/{hidden.id}/bookmark").status_code == 401
    res = client.put(f"/api/v1/fairs/{hidden.id}/bookmark", headers=f.auth_header(f.user(db)))
    assert res.status_code == 404
