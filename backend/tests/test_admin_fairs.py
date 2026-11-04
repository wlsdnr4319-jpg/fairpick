"""관리자 박람회 등록·수정·숨김 (F-08)."""

import pytest

from tests import factories as f


@pytest.fixture
def ctx(db):
    cat = f.category(db, "food", "식음료")
    ven = f.venue(db, name="코엑스")
    f.tag(db, "date", "데이트 추천")
    f.tag(db, "tasting", "시식·시음 있음")
    return {"cat": cat, "ven": ven, "h": f.auth_header(f.admin(db))}


def _body(ctx, **over):
    return {
        "title": "서울 디저트 페어",
        "category": "food",
        "venue_id": ctx["ven"].id,
        "start_date": "2026-12-10",
        "end_date": "2026-12-13",
        "public_access": "public",
        "price_onsite": 15000,
        "price_prereg": 0,
        "prereg_end_at": "2026-12-08T23:59:00+09:00",
        "official_url": "https://example.com",
        "tags": ["date", "tasting"],
        **over,
    }


def test_create_draft_then_publish(db, client, ctx):
    res = client.post("/api/v1/admin/fairs", json=_body(ctx), headers=ctx["h"])
    assert res.status_code == 201, res.text
    fair = res.json()
    assert fair["status"] == "draft" and fair["source"] == "manual"
    assert fair["tags"] == ["date", "tasting"]
    assert fair["prereg_end_at"] == "2026-12-08T23:59:00+09:00"  # UTC 로 저장했다가 KST 로 돌려준다
    assert fair["verified_at"] is None

    # 초안은 일반 사용자에게 보이지 않는다
    assert client.get(f"/api/v1/fairs/{fair['id']}").status_code == 404

    res = client.patch(
        f"/api/v1/admin/fairs/{fair['id']}",
        json={"status": "published", "visit_tip": "평일 오전이 한산해요", "tags": ["date"], "verified": True},
        headers=ctx["h"],
    )
    assert res.status_code == 200, res.text
    assert res.json()["tags"] == ["date"] and res.json()["verified_at"] is not None

    detail = client.get(f"/api/v1/fairs/{fair['id']}").json()
    assert detail["visit_tip"] == "평일 오전이 한산해요"
    assert detail["prereg"]["end_at"] == "2026-12-08T23:59:00+09:00"


def test_hide_instead_of_delete(db, client, ctx):
    fair = f.fair(db, category=ctx["cat"], venue=ctx["ven"])
    res = client.patch(f"/api/v1/admin/fairs/{fair.id}", json={"status": "hidden"}, headers=ctx["h"])
    assert res.status_code == 200
    assert client.get(f"/api/v1/fairs/{fair.id}").status_code == 404
    rows = client.get("/api/v1/admin/fairs?status=hidden", headers=ctx["h"]).json()
    assert [r["id"] for r in rows["items"]] == [fair.id]


@pytest.mark.parametrize(
    "over",
    [
        {"end_date": "2026-12-01"},  # 끝 < 시작
        {"category": "nope"},
        {"venue_id": 999999},
        {"tags": ["no-such-tag"]},
        {"price_onsite": -1},
        {"official_url": "not a url"},
    ],
)
def test_create_validation(client, ctx, over):
    res = client.post("/api/v1/admin/fairs", json=_body(ctx, **over), headers=ctx["h"])
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_patch_period_check_uses_merged_values(db, client, ctx):
    fair = f.fair(db, category=ctx["cat"], venue=ctx["ven"])  # 11.19 ~ 11.22
    res = client.patch(f"/api/v1/admin/fairs/{fair.id}", json={"end_date": "2026-11-01"}, headers=ctx["h"])
    assert res.status_code == 422


def test_unknown_fair(client, ctx):
    assert client.patch("/api/v1/admin/fairs/999999", json={}, headers=ctx["h"]).status_code == 404
