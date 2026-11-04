"""
코엑스 행사 일정 파서. 목록: https://www.coex.co.kr/event/full-schedules/

robots.txt (2026-11-04 확인): 일반 크롤러는 /wp-admin/, /wp-content/uploads/ 만 금지. 일정 페이지는 허용.
목록은 search_start_date, search_end_date(YYYY.MM.DD)로 기간을 고르고 var_page 로 페이지를 넘긴다.
행사 구분이 Convention(학회·세미나)인 항목은 일반인 대상이 아닌 경우가 대부분이라 건너뛴다.
"""

import calendar
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup

from app.crawlers.base import BaseParser, RawFair, clean_text, venue_text
from app.crawlers.registry import register

LIST_URL = "https://www.coex.co.kr/event/full-schedules/"
SKIP_KINDS = {"convention"}
MAX_PAGES = 10


@register
class CoexParser(BaseParser):
    parser_key = "coex"

    def fetch_list(self, year: int, month: int) -> list[RawFair]:
        last = calendar.monthrange(year, month)[1]
        items: dict[str, RawFair] = {}
        for page in range(1, MAX_PAGES + 1):
            html = self.client.get(
                LIST_URL,
                params={
                    "var_page": page,
                    "search_start_date": f"{year}.{month:02d}.01",
                    "search_end_date": f"{year}.{month:02d}.{last:02d}",
                    "list_type": "LIST",
                },
            )
            found = self.parse_list(html)
            new = [f for f in found if f.external_id not in items]
            if not new:
                break
            items.update((f.external_id, f) for f in new)
        return list(items.values())

    def parse_list(self, html: str) -> list[RawFair]:
        soup = BeautifulSoup(html, "html.parser")
        out = []
        for link in soup.select("li.BlogPost-item a.BlogEventItem-link"):
            cont = link.select_one(".BlogEventItemCont-inner")
            title = _text(cont, ".BlogEventItemCont-tit")
            period = _text(cont, ".BlogEventItemCont-date")
            if not title or not period:
                continue
            kind = _text(cont, ".BlogEventItemCont-cate")
            if kind.casefold() in SKIP_KINDS:
                continue
            hall = _text(cont, ".BlogEventItemCont-hall")
            # 상세 URL 의 검색 조건(query)은 떼어 내 행사 ID 로 쓴다
            parts = urlsplit(link["href"])
            detail = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
            out.append(
                RawFair(
                    external_id=parts.path,
                    title=title,
                    period_text=period,
                    venue_text=venue_text("코엑스", hall),
                    detail_url=detail,
                    extra={"kind": kind, "hall": hall},
                )
            )
        return out


def _text(node, selector: str) -> str:
    el = node.select_one(selector) if node else None
    return clean_text(el.get_text(" ")) if el else ""
