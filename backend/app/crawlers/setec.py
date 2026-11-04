"""
SETEC(서울무역전시컨벤션센터) 전시 일정 파서. 목록: https://www.setec.or.kr/front/schedule/list.do

robots.txt (2026-11-04 확인): Googlebot 의 /search/search.do, /bbs/ 만 금지. 일반 크롤러 제한 없음.
목록은 오늘 이후 행사를 개막순으로 12개씩 보여주고 pageIndex 로 페이지를 넘긴다 (월 지정 없음).
상세는 view.do?sIdx=<행사 번호>. 행사 구분이 없어 학회·설명회도 섞여 있다 → 검수에서 거른다.
"""

import re

from bs4 import BeautifulSoup

from app.crawlers.base import BaseParser, RawFair, clean_text, venue_text
from app.crawlers.registry import register

LIST_URL = "https://www.setec.or.kr/front/schedule/list.do"
DETAIL_URL = "https://www.setec.or.kr/front/schedule/view.do?sIdx={idx}"
MAX_PAGES = 10
_IDX = re.compile(r"fn_view\('(\d+)'\)")
_LABEL = re.compile(r"^\s*(기간|장소)\s*:\s*")


@register
class SetecParser(BaseParser):
    parser_key = "setec"
    monthly = False

    def fetch_list(self, year: int, month: int) -> list[RawFair]:
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
        for link in soup.select(".exhibit_list a[onclick]"):
            m = _IDX.search(link.get("onclick", ""))
            title_el = link.select_one(".txt strong")
            if not (m and title_el):
                continue
            fields = {}
            for li in link.select(".txt li"):
                text = clean_text(li.get_text(" "))
                label = _LABEL.match(text)
                if label:
                    fields[label.group(1)] = text[label.end() :]
            title = clean_text(title_el.get_text(" "))
            period = fields.get("기간", "")
            if not (title and period):
                continue
            hall = fields.get("장소", "")
            idx = m.group(1)
            out.append(
                RawFair(
                    external_id=idx,
                    title=title,
                    period_text=period,
                    venue_text=venue_text("SETEC", hall),
                    detail_url=DETAIL_URL.format(idx=idx),
                    extra={"hall": hall},
                )
            )
        return out
