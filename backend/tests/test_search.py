"""
ngram 전문 검색 (11주차). InnoDB FULLTEXT 인덱스는 커밋된 행만 보이므로,
이 테스트는 데이터를 실제로 커밋하고 끝나면 지운다.
"""

from datetime import date

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import Category, Fair, Venue


@pytest.fixture
def committed(db_engine):
    with Session(db_engine) as s:
        cat = Category(code="ft-food", name="식음료")
        ven = Venue(name="검색테스트홀", region="서울")
        s.add_all([cat, ven])
        s.flush()
        rows = [
            ("제25회 서울카페쇼", "국내 최대 커피 전시"),
            ("메가푸드쇼 2026", "간편식과 디저트 할인"),
            ("서울 와인 페스티벌", "내추럴 와인 시음"),
        ]
        for title, summary in rows:
            s.add(
                Fair(
                    title=title,
                    summary=summary,
                    category_id=cat.id,
                    venue_id=ven.id,
                    start_date=date(2026, 12, 1),
                    end_date=date(2026, 12, 2),
                    status="published",
                    source="manual",
                )
            )
        s.commit()
        ids = (cat.id, ven.id)
    yield
    with Session(db_engine) as s:
        s.execute(delete(Fair).where(Fair.venue_id == ids[1]))
        s.execute(delete(Venue).where(Venue.id == ids[1]))
        s.execute(delete(Category).where(Category.id == ids[0]))
        s.commit()


def _q(client, q):
    res = client.get("/api/v1/fairs", params={"q": q, "size": 50})
    assert res.status_code == 200
    return sorted(i["title"] for i in res.json()["items"])


def test_fulltext_title_summary_and_all_words(committed, db, client):
    assert _q(client, "카페") == ["제25회 서울카페쇼"]  # 단어 중간도 찾는다 (ngram)
    assert _q(client, "디저트") == ["메가푸드쇼 2026"]  # 소개글
    assert _q(client, "서울 와인") == ["서울 와인 페스티벌"]  # 모든 단어를 포함
    assert _q(client, "쇼") == ["메가푸드쇼 2026", "제25회 서울카페쇼"]  # 한 글자는 LIKE


def test_boolean_operators_are_ignored(committed, db, client):
    # 연산자는 글자 그대로 무시한다: '+카페' = '카페', '-와인' 은 제외가 아니라 '와인' 도 포함해야 한다
    assert _q(client, "+카페") == ["제25회 서울카페쇼"]
    assert _q(client, '"카페" -와인') == []
    assert _q(client, "()~*") == []
