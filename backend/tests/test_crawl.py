"""수집 작업(중복 판정·변경 감지)과 검수 API (F-09, F-10)."""

from datetime import date, datetime

import pytest
from sqlalchemy import select

from app.crawlers.base import BaseParser, RawFair
from app.models import CrawledItem, CrawlRun, CrawlSource, VenueAlias
from app.services.crawl import run_source
from tests import factories as f
from tests.conftest import TODAY

NOW = datetime(2026, 11, 3, 19, 0)  # = 11.04 04:00 KST


class FakeParser(BaseParser):
    """네트워크 없이 정해진 목록을 돌려주는 파서."""

    parser_key = "fake"
    monthly = False
    pages: list[RawFair] = []
    fail = False

    def fetch_list(self, year, month):
        if self.fail:
            raise RuntimeError("사이트 구조가 바뀜")
        return list(self.pages)

    def parse_list(self, html):
        return []


def raw(eid="A1", title="서울 디저트 페어", period="2026.12.10 - 2026.12.13", venue="코엑스 Hall B"):
    return RawFair(external_id=eid, title=title, period_text=period, venue_text=venue, detail_url=f"https://x/{eid}")


@pytest.fixture
def source(db):
    ven = f.venue(db, name="코엑스")
    db.add(VenueAlias(venue_id=ven.id, alias="COEX"))
    src = CrawlSource(venue_id=ven.id, parser_key="fake", list_url="https://x/list")
    db.add(src)
    db.flush()
    return src


def _run(db, source, pages, fail=False):
    FakeParser.pages, FakeParser.fail = pages, fail
    return run_source(db, source, today=TODAY, now=NOW, parser_factory=FakeParser)


def _items(db):
    return {i.external_id: i for i in db.scalars(select(CrawledItem))}


def test_new_unchanged_changed(db, source):
    run = _run(db, source, [raw(), raw("A2", "와인 위크", "2026.11.20 - 2026.11.22", "COEX Hall C")])
    assert (run.status, run.found_count, run.new_count, run.changed_count) == ("succeeded", 2, 2, 0)
    item = _items(db)["A1"]
    assert (item.parsed_start_date, item.parsed_end_date) == (date(2026, 12, 10), date(2026, 12, 13))
    assert item.parsed_venue_id == source.venue_id
    assert (item.change_status, item.review_status) == ("new", "pending")
    assert _items(db)["A2"].parsed_venue_id == source.venue_id  # 별칭 COEX 로 매칭

    # 같은 내용이면 unchanged, 검수 상태는 그대로
    item.review_status = "rejected"
    db.flush()
    run = _run(db, source, [raw()])
    assert (run.new_count, run.changed_count) == (0, 0)
    assert (_items(db)["A1"].change_status, _items(db)["A1"].review_status) == ("unchanged", "rejected")

    # 기간이 바뀌면 changed 로 표시하고 검수 대기로 되돌린다
    run = _run(db, source, [raw(period="2026.12.11 - 2026.12.14")])
    assert run.changed_count == 1
    assert (_items(db)["A1"].change_status, _items(db)["A1"].review_status) == ("changed", "pending")


def test_unparseable_period_is_kept_with_null_dates(db, source):
    _run(db, source, [raw(period="일정 추후 공지")])
    item = _items(db)["A1"]
    assert item.parsed_start_date is None and item.review_status == "pending"


def test_failed_run_is_recorded(db, source):
    run = _run(db, source, [], fail=True)
    assert run.status == "failed"
    assert "사이트 구조가 바뀜" in run.error_message
    assert db.get(CrawlRun, run.id).finished_at is not None


@pytest.fixture
def admin_h(db):
    f.category(db, "food", "식음료")
    f.tag(db, "date", "데이트 추천")
    return f.auth_header(f.admin(db))


def _approve_body(source, **over):
    return {
        "title": "서울 디저트 페어",
        "category": "food",
        "venue_id": source.venue_id,
        "hall": "Hall B",
        "start_date": "2026-12-10",
        "end_date": "2026-12-13",
        "public_access": "public",
        "status": "published",
        "tags": ["date"],
        **over,
    }


def test_review_queue_approve_creates_crawler_fair(db, client, source, admin_h):
    _run(db, source, [raw()])
    queue = client.get("/api/v1/admin/crawled-items", headers=admin_h).json()
    assert queue["total"] == 1
    item = queue["items"][0]
    assert item["parsed_venue_name"] == "코엑스" and item["raw_payload"]["title"] == "서울 디저트 페어"

    res = client.post(f"/api/v1/admin/crawled-items/{item['id']}/approve", json=_approve_body(source), headers=admin_h)
    assert res.status_code == 200, res.text
    fair = res.json()
    assert fair["source"] == "crawler" and fair["status"] == "published"
    assert db.get(CrawledItem, item["id"]).fair_id == fair["id"]
    assert client.get(f"/api/v1/fairs/{fair['id']}").status_code == 200

    # 한 번 검수한 항목은 다시 처리할 수 없다
    again = client.post(f"/api/v1/admin/crawled-items/{item['id']}/reject", headers=admin_h)
    assert again.status_code == 409 and again.json()["error"]["code"] == "ALREADY_REVIEWED"


def test_merge_candidates_and_merge(db, client, source, admin_h):
    existing = f.fair(
        db,
        category=f.category(db, "culture", "문화"),
        venue=source_venue(db, source),
        title="2026 서울 디저트페어",
        start=date(2026, 12, 10),
        end=date(2026, 12, 13),
    )
    _run(db, source, [raw()])
    item = client.get("/api/v1/admin/crawled-items", headers=admin_h).json()["items"][0]
    assert item["merge_candidates"][0]["fair_id"] == existing.id

    res = client.post(f"/api/v1/admin/crawled-items/{item['id']}/merge", json={"fair_id": existing.id}, headers=admin_h)
    assert res.status_code == 200 and res.json()["review_status"] == "merged"


def source_venue(db, source):
    from app.models import Venue

    return db.get(Venue, source.venue_id)


def test_reject_and_admin_only(db, client, source, admin_h):
    _run(db, source, [raw()])
    item_id = db.scalar(select(CrawledItem.id))
    assert (
        client.post(f"/api/v1/admin/crawled-items/{item_id}/reject", headers=f.auth_header(f.user(db))).status_code
        == 403
    )
    res = client.post(f"/api/v1/admin/crawled-items/{item_id}/reject", headers=admin_h)
    assert res.json()["review_status"] == "rejected"
    assert client.get("/api/v1/admin/crawled-items", headers=admin_h).json()["total"] == 0


def test_runs_and_sources_listing(db, client, source, admin_h):
    _run(db, source, [raw()])
    runs = client.get("/api/v1/admin/crawl-runs", headers=admin_h).json()
    assert runs["items"][0]["status"] == "succeeded" and runs["items"][0]["new_count"] == 1
    sources = client.get("/api/v1/admin/crawl-sources", headers=admin_h).json()
    assert sources[0]["parser_key"] == "fake" and sources[0]["last_run_status"] == "succeeded"
