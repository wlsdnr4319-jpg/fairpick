"""
엑스코(EXCO, 대구) 행사 일정 파서. 연간 일정표: https://www.exco.co.kr/schedule/schedule_list.html

robots.txt (2026-11-04 확인): 일반 크롤러는 /Develop/, /deditor/, /data/ 와 일부 게시판만 금지. 일정표 허용.
행사일정 화면(/schedule/sub01.html)은 자바스크립트로 목록을 불러오지만, 인쇄용 연간 일정표는 정적 HTML 표다.
?syear=2026&ex_cate=1 로 연도와 분류(1 = 전시회)를 고른다. 페이지 나눔이 없다.

표에는 행사 번호도 상세 링크도 없다. 그래서 '개막일:행사명' 을 external_id 로 쓴다.
같은 해에 같은 이름으로 여러 번 열리는 행사(웨딩박람회 등)가 있어 연도만으로는 겹친다.
개막일이나 이름이 바뀌면 새 항목으로 잡힌다 (검수 화면에서 기존 박람회의 병합 후보로 보인다).
주최자 전화번호는 저장하지 않는다.
"""

import re
from datetime import date

from bs4 import BeautifulSoup

from app.crawlers.base import BaseParser, RawFair, clean_text
from app.crawlers.normalize import PeriodParseError, parse_period
from app.crawlers.registry import register

LIST_URL = "https://www.exco.co.kr/schedule/schedule_list.html"
EXHIBITION = "1"  # ex_cate: 1 전시회, 2 회의/컨벤션, 4 공연/이벤트
KEEP_KINDS = {"전시회"}
VENUE = "엑스코"
_START = re.compile(r"\d{4}-\d{2}-\d{2}")


@register
class ExcoParser(BaseParser):
    parser_key = "exco"
    monthly = False

    def fetch_list(self, year: int, month: int) -> list[RawFair]:
        # 연간 표라 지난 행사도 들어 있다. 이번 달 1일 이후에 끝나는 행사만 남긴다
        years = [year, year + 1] if month >= 10 else [year]  # 연말에는 내년 표도 본다
        since = date(year, month, 1)
        out: dict[str, RawFair] = {}
        for y in years:
            html = self.client.get(LIST_URL, params={"syear": y, "ex_cate": EXHIBITION})
            for raw in self.parse_list(html):
                if _ends_before(raw.period_text, since):
                    continue
                out.setdefault(raw.external_id, raw)
        return list(out.values())

    def parse_list(self, html: str) -> list[RawFair]:
        soup = BeautifulSoup(html, "html.parser")
        out = []
        for row in soup.select("table.tb_base tbody tr"):
            cells = [clean_text(td.get_text(" ")) for td in row.select("td")]
            if len(cells) < 6:
                continue
            _no, kind, title, organizer, _phone, period = cells[:6]
            if kind not in KEEP_KINDS or not (title and period):
                continue
            start = _START.search(period)
            if not start:
                continue
            out.append(
                RawFair(
                    external_id=f"{start.group(0)}:{title}"[:200],
                    title=title,
                    period_text=period,
                    venue_text=VENUE,
                    detail_url=f"{LIST_URL}?syear={start.group(0)[:4]}&ex_cate={EXHIBITION}",
                    extra={"kind": kind, "organizer": organizer},
                )
            )
        return out


def _ends_before(period_text: str, since: date) -> bool:
    try:
        return parse_period(period_text)[1] < since
    except PeriodParseError:
        return False  # 못 읽는 기간은 남겨서 검수에서 본다
