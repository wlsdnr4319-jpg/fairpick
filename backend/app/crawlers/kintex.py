"""
킨텍스 행사 일정 파서. 목록: https://www.kintex.com/web/ko/event/list.do

robots.txt (2026-11-04 확인): 일반 크롤러는 /admin/, /login/ 만 금지. 행사 목록은 허용.
목록은 기본으로 오늘부터 한 달 치를 보여주고 pageIndex 로 페이지를 넘긴다. 상세는 view.do?seq=<행사 번호>.
행사 구분이 회의(학회·세미나)인 항목은 건너뛴다.
"""

import re

from bs4 import BeautifulSoup

from app.crawlers.base import BaseParser, RawFair, clean_text, venue_text
from app.crawlers.registry import register

LIST_URL = "https://www.kintex.com/web/ko/event/list.do"
DETAIL_URL = "https://www.kintex.com/web/ko/event/view.do?seq={seq}"
SKIP_KINDS = {"회의"}
MAX_PAGES = 10
_SEQ = re.compile(r"fnView\('[^']*',\s*(\d+)\)")


@register
class KintexParser(BaseParser):
    parser_key = "kintex"
    monthly = False

    def fetch_list(self, year: int, month: int) -> list[RawFair]:
        # 킨텍스 목록은 월 지정 대신 오늘부터 한 달 치를 보여준다 (monthly = False)
        items: dict[str, RawFair] = {}
        for page in range(1, MAX_PAGES + 1):
            found = self.parse_list(self.client.get(LIST_URL, params={"pageIndex": page}))
            new = [f for f in found if f.external_id not in items]
            if not new:
                break
            items.update((f.external_id, f) for f in new)
        return list(items.values())

    def parse_list(self, html: str) -> list[RawFair]:
        soup = BeautifulSoup(html, "html.parser")
        out = []
        for link in soup.select(".schedule-board-list a.btn-square-item"):
            m = _SEQ.search(link.get("href", ""))
            title = _text(link, ".item-subject")
            period = _text(link, ".item-date")
            if not (m and title and period):
                continue
            kind = _text(link, ".event-label-ko")
            if kind in SKIP_KINDS:
                continue
            hall = _text(link, ".item-client")
            seq = m.group(1)
            out.append(
                RawFair(
                    external_id=seq,
                    title=title,
                    period_text=period,
                    venue_text=venue_text("킨텍스", hall),
                    detail_url=DETAIL_URL.format(seq=seq),
                    extra={"kind": kind, "hall": hall},
                )
            )
        return out


def _text(node, selector: str) -> str:
    el = node.select_one(selector)
    return clean_text(el.get_text(" ")) if el else ""
