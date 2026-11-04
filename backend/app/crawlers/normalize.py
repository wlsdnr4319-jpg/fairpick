"""
정규화 함수 (레퍼런스 8장 정규화 규칙). DB 나 네트워크에 의존하지 않는 순수 함수라 단위 테스트를 촘촘히 붙인다.

기간: "2026.11.19(목) ~ 11.22(일)", "2026-11-19 ~ 2026-11-22", "11월 19일~22일" 같은 표기를 start, end 로 바꾼다.
      끝 날짜에 연도나 월이 없으면 시작 날짜에서 가져온다. "12.30 ~ 1.2"처럼 해를 넘기면 끝 연도에 1을 더한다.
장소: 별칭으로 "COEX", "서울 코엑스", "코엑스 A홀"을 모두 코엑스로 맞추고, 남은 "A홀"은 hall 에 넣는다.
"""

import hashlib
import re
from datetime import date

# 날짜 하나: (연)(월)(일). 구분자는 . - / 또는 년 월 일
_DATE = re.compile(
    r"""
    (?:(?P<y>\d{4})\s*[.\-/년]\s*)?     # 연도 (선택)
    (?:(?P<m>\d{1,2})\s*[.\-/월]\s*)?   # 월 (선택)
    (?P<d>\d{1,2})\s*일?                # 일
    """,
    re.VERBOSE,
)
_WEEKDAY = re.compile(r"\([월화수목금토일]\)|\((?:mon|tue|wed|thu|fri|sat|sun)\)", re.IGNORECASE)
_SEP = re.compile(r"\s*[~∼〜–—]\s*|\s+-\s+")


class PeriodParseError(ValueError):
    pass


def _parts(text: str) -> tuple[int | None, int | None, int]:
    m = _DATE.fullmatch(text.strip().rstrip("."))
    if not m:
        raise PeriodParseError(f"날짜를 읽을 수 없어요: {text!r}")
    y = int(m["y"]) if m["y"] else None
    mo = int(m["m"]) if m["m"] else None
    return y, mo, int(m["d"])


def parse_period(text: str, ref_year: int | None = None) -> tuple[date, date]:
    """기간 문자열 → (시작일, 종료일). 하루짜리면 둘이 같다. 읽을 수 없으면 PeriodParseError."""
    cleaned = _WEEKDAY.sub("", text).replace(" ", " ").strip()
    pieces = _SEP.split(cleaned, maxsplit=1)
    if len(pieces) == 1:
        # "2026-11-19" 처럼 하이픈이 날짜 구분자인 하루짜리
        pieces = [cleaned, cleaned]

    sy, sm, sd = _parts(pieces[0])
    ey, em, ed = _parts(pieces[1])

    sy = sy or ref_year
    if sy is None or sm is None:
        raise PeriodParseError(f"시작 날짜에 연도나 월이 없어요: {text!r}")
    end_year_given = ey is not None
    em = em or sm
    ey = ey or sy
    try:
        start = date(sy, sm, sd)
        end = date(ey, em, ed)
    except ValueError as exc:
        raise PeriodParseError(f"없는 날짜예요: {text!r}") from exc

    if end < start and not end_year_given:
        # 끝 연도를 생략했는데 시작보다 앞이면 해를 넘긴 것: "12.30 ~ 1.2"
        end = date(sy + 1, em, ed)
    if end < start:
        raise PeriodParseError(f"끝 날짜가 시작 날짜보다 빨라요: {text!r}")
    return start, end


def _key(text: str) -> str:
    return re.sub(r"[\s()\[\]·,]", "", text).casefold()


def match_venue(text: str, aliases: dict[str, int]) -> tuple[int | None, str | None]:
    """
    장소 문자열 → (venue_id, 전시홀). aliases 는 {별칭 또는 전시장 이름: venue_id}.
    가장 길게 일치하는 별칭을 쓴다. 예: "서울 코엑스 A홀" → (코엑스 id, "A홀")
    """
    if not text:
        return None, None
    key = _key(text)
    best: tuple[int, int, str] | None = None  # (일치 길이, venue_id, 별칭 key)
    for alias, venue_id in aliases.items():
        a = _key(alias)
        if a and key.startswith(a) and (best is None or len(a) > best[0]):
            best = (len(a), venue_id, a)
    if best is None:
        return None, None

    # 원문에서 별칭 부분을 떼고 남은 글자를 전시홀로 본다
    consumed, rest = 0, text.strip()
    for i, ch in enumerate(rest):
        if _key(ch):
            consumed += 1
        if consumed == best[0]:
            rest = rest[i + 1 :]
            break
    hall = rest.strip(" ,·-") or None
    return best[1], hall


def content_hash(title: str, period: str, venue: str) -> str:
    """제목·기간·장소 문자열로 만든다. 조회수처럼 매번 바뀌는 값은 넣지 않는다."""
    raw = "\x1f".join(re.sub(r"\s+", " ", s or "").strip() for s in (title, period, venue))
    return hashlib.sha256(raw.encode()).hexdigest()
