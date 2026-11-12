"""
수원메쎄 행사 일정 파서. 달력: https://suwonmesse.com/event_schedule/event_calendar/

robots.txt (2026-11-04 확인): 모든 크롤러 허용 (Disallow 비어 있음).
목록이 없고 월별 달력만 있다 (?mod=calendar&kboard_calendar_year=2026&kboard_calendar_month=11).
행사는 열리는 날짜 칸마다 반복해서 나오므로, 같은 uid 가 나온 날짜를 모아 가장 이른 날 ~ 가장 늦은 날을 기간으로 만든다.
달을 넘기는 행사(11.30 ~ 12.2)가 잘리지 않도록 지난달부터 몇 달을 한 번에 받아 합친다 (monthly = False, calendar.py).
"""

from datetime import date

from bs4 import BeautifulSoup

from app.crawlers.base import BaseParser, RawFair, clean_text
from app.crawlers.calendar import MONTH_OFFSETS, CalendarEvent, merge, shift_month, to_raw
from app.crawlers.registry import register

CALENDAR_URL = "https://suwonmesse.com/event_schedule/event_calendar/"
DETAIL_URL = "https://suwonmesse.com/event_schedule/event_calendar/?uid={uid}&mod=document"
VENUE = "수원메쎄"
# 분류는 전시·이벤트·회의. 회의(교육·세미나·설명회)는 박람회가 아니라 건너뛴다 (코엑스·코엑스 마곡과 같은 기준)
SKIP_KINDS = {"회의"}
# 이름 없이 비워 두거나 '행사'·'비공개행사'라고만 적힌 대관 칸
PLACEHOLDER_TITLES = {"", "행사", "비공개행사", "전시박람회"}


@register
class SuwonMesseParser(BaseParser):
    parser_key = "suwonmesse"
    monthly = False

    def fetch_list(self, year: int, month: int) -> list[RawFair]:
        events: dict[str, CalendarEvent] = {}
        for offset in MONTH_OFFSETS:
            merge(events, self.fetch_month(*shift_month(year, month, offset)))
        return to_raw(events, since=date(year, month, 1))

    def fetch_month(self, year: int, month: int) -> dict[str, CalendarEvent]:
        """달력 한 달 치. 지난 행사 수집(backfill_archive)도 이걸 쓴다."""
        html = self.client.get(
            CALENDAR_URL, params={"mod": "calendar", "kboard_calendar_year": year, "kboard_calendar_month": month}
        )
        return collect(html)

    def parse_list(self, html: str) -> list[RawFair]:
        return to_raw(collect(html))


def collect(html: str) -> dict[str, CalendarEvent]:
    """달력 한 달 치 → {uid: 행사}. 표시 중인 연·월은 페이지의 선택 상자에서 읽는다."""
    soup = BeautifulSoup(html, "html.parser")
    year_el = soup.select_one('select[name="kboard_calendar_year"] option[selected]')
    month_el = soup.select_one('select[name="kboard_calendar_month"] option[selected]')
    if not (year_el and month_el):
        return {}
    year, month = int(year_el.get_text(strip=True)), int(month_el.get_text(strip=True))

    events: dict[str, CalendarEvent] = {}
    for cell in soup.select("table.kboard-calendar-table td"):
        # 앞뒤 달 날짜로 채운 칸은 건너뛴다 (그 달 페이지에서 다시 나온다)
        if "calendar-column-pre-next-day" in (cell.get("class") or []):
            continue
        day_el = cell.select_one(".calendar-icon-day")
        if day_el is None or not day_el.get_text(strip=True).isdigit():
            continue
        day = date(year, month, int(day_el.get_text(strip=True)))
        for link in cell.select(".calendar-event a[href]"):
            uid = _uid(link["href"])
            title_el = link.select_one(".event-name")
            if not (uid and title_el):
                continue
            kind_el = link.select_one(".classification")
            kind = clean_text(kind_el.get_text(" ")) if kind_el else ""
            title = clean_text(title_el.get_text(" "))
            if kind in SKIP_KINDS or title in PLACEHOLDER_TITLES:
                continue
            event = events.setdefault(
                uid,
                CalendarEvent(
                    title=title,
                    kind=kind,
                    detail_url=DETAIL_URL.format(uid=uid),
                    venue_text=VENUE,
                ),
            )
            event.days.add(day)
    return events


def _uid(href: str) -> str:
    for part in href.split("?", 1)[-1].split("&"):
        key, _, value = part.partition("=")
        if key == "uid" and value.isdigit():
            return value
    return ""
