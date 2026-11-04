"""
코엑스 마곡 행사 일정 파서. 달력: https://coexmagok.co.kr/event-schedule/

robots.txt (2026-11-04 확인): /wp-admin/ 만 금지하고 /wp-admin/admin-ajax.php 는 허용.
일정은 달력형만 있다. 첫 화면은 이번 달 달력이고, 다른 달은 admin-ajax.php 에
action=change_ex_month 를 POST 해서 받는다. 응답: "OK^연도^월^칸 HTML^달력 첫날^달력 마지막날".

달력 칸은 '달력 첫날'(앞달 일요일)부터 하루씩 이어지므로 칸 순서로 날짜를 계산하고, 칸의 일(日) 숫자로 검증한다.
행사 색으로 분류를 구분한다: pink 전시, purple 컨벤션(학회·설명회), yellow 이벤트.
컨벤션은 건너뛴다 (코엑스와 같은 기준).
"""

from datetime import date, timedelta
from urllib.parse import unquote, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from app.crawlers.base import BaseParser, RawFair, clean_text
from app.crawlers.calendar import CalendarEvent, merge, shift_month, to_raw
from app.crawlers.registry import register

PAGE_URL = "https://coexmagok.co.kr/event-schedule/"
AJAX_URL = "https://coexmagok.co.kr/wp-admin/admin-ajax.php"
VENUE = "코엑스 마곡"
KINDS = {"pink": "Exhibition", "purple": "Convention", "yellow": "Event"}
SKIP_KINDS = {"Convention"}


class CalendarLayoutError(ValueError):
    """칸 날짜 계산이 화면의 일(日) 숫자와 어긋남 = 사이트 구조가 바뀜. 수집 실패로 기록해 알림을 받는다."""


@register
class CoexMagokParser(BaseParser):
    parser_key = "coexmagok"
    monthly = False

    def fetch_list(self, year: int, month: int) -> list[RawFair]:
        # 첫 화면은 사이트 기준 이번 달. 그 달을 기준으로 지난달·다음 달·다다음 달을 AJAX 로 받는다
        html = self.client.get(PAGE_URL)
        events = collect_page(html)
        base_y, base_m = page_month(html)
        for flag, (y, m) in (
            ("PREV", (base_y, base_m)),
            ("NEXT", (base_y, base_m)),
            ("NEXT", shift_month(base_y, base_m, 1)),
        ):
            text = self.client.post(
                AJAX_URL,
                data={
                    "action": "change_ex_month",
                    "change_flag": flag,
                    "current_year": y,
                    "current_month": m,
                    "search_keyword": "",
                    "search_type": "",
                    "search_dept": "",
                },
            )
            merge(events, collect_ajax(text))
        return to_raw(events, since=date(year, month, 1))

    def parse_list(self, html: str) -> list[RawFair]:
        return to_raw(collect_page(html))


def page_month(html: str) -> tuple[int, int]:
    soup = BeautifulSoup(html, "html.parser")
    y = soup.select_one("#calendar_year")
    m = soup.select_one("#calendar_month")
    if not (y and m):
        raise CalendarLayoutError("calendar_year/calendar_month 를 찾을 수 없어요")
    return int(y["value"]), int(m["value"])


def collect_page(html: str) -> dict[str, CalendarEvent]:
    """첫 화면 HTML → {행사 경로: 행사}. 달력이 없으면 빈 dict."""
    soup = BeautifulSoup(html, "html.parser")
    start = soup.select_one("#search_start_date")
    body = soup.select_one("#EX_CALENDAR_DATA")
    if not (start and body and start.get("value")):
        return {}
    return _collect_cells(body.select(":scope > .PostCalendarTbody-item"), date.fromisoformat(start["value"]))


def collect_ajax(text: str) -> dict[str, CalendarEvent]:
    """AJAX 응답 "OK^연도^월^칸 HTML^첫날^마지막날" → {행사 경로: 행사}."""
    parts = text.strip().split("^")
    if len(parts) < 6 or parts[0] != "OK":
        raise CalendarLayoutError(f"예상과 다른 달력 응답: {text[:80]!r}")
    soup = BeautifulSoup(parts[3], "html.parser")
    return _collect_cells(soup.select(".PostCalendarTbody-item"), date.fromisoformat(parts[4]))


def _collect_cells(cells, first_day: date) -> dict[str, CalendarEvent]:
    events: dict[str, CalendarEvent] = {}
    for index, cell in enumerate(cells):
        day = first_day + timedelta(days=index)
        num = cell.select_one(".PostCalendarTbody-num")
        if num is None or num.get_text(strip=True) != str(day.day):
            raise CalendarLayoutError(f"{index}번째 칸 날짜가 {day} 와 맞지 않아요")
        for link in cell.select("a.PostCalendarTbody-txt[href]"):
            kind = next((KINDS[c] for c in link.get("class", []) if c in KINDS), "")
            if kind in SKIP_KINDS:
                continue
            title = clean_text(link.get_text(" "))
            parts = urlsplit(link["href"])
            path = "/" + "/".join(p for p in parts.path.split("/") if p) + "/"  # 'slug//' 같은 중복 슬래시 정리
            if not title or not path.startswith("/exhibitions/"):
                continue
            key = unquote(path)[:255]  # 한글 slug 를 그대로 ID 로 (인코딩하면 3배 길어진다)
            event = events.setdefault(
                key,
                CalendarEvent(
                    title=title,
                    kind=kind,
                    detail_url=urlunsplit((parts.scheme, parts.netloc, path, "", "")),
                    venue_text=VENUE,
                ),
            )
            event.days.add(day)
    return events
