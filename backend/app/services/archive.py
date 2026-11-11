"""
지난 행사 기록 (fair_archive) 저장과 주제 분류.

주제는 제목 키워드로 나눈다. RULES 를 위에서부터 보며 처음 맞는 주제 하나만 붙인다.
제목은 소문자로 바꾸고 띄어쓰기를 지운 뒤 비교한다 ('명절 선물전' = '명절선물전'). 키워드도 띄어쓰기 없이 적는다.

순서가 곧 우선순위다.
  1. 입주박람회 — 새 아파트 입주민 대상 행사. 통계에서 뺀다
  2. 학술대회·상담회처럼 B2B 가 분명한 행사 — '미용의료기기 학술대회'가 뷰티로, '학회 정기총회 및 학술대회'가
     '박람회 아님'으로 가지 않게 먼저 본다
  3. 박람회 아님 — 선거 개표, 공연, 면세점 행사처럼 전시장 일정표에 섞여 있는 다른 행사. 통계에서 뺀다
  4. 일반인 주제 — 취업·창업을 앞에 둔다 ('외국인유학생 채용박람회', '농식품 스타트업 창업박람회')
  5. 산업·학술 — '산업', '기술' 같은 넓은 말은 일반인 주제를 다 본 뒤에 ('건강산업박람회'는 뷰티·건강)

'아트'(스마트), '티'(파티), '술'(기술), 'ev'(event), 'tea'(team)처럼 다른 낱말 속에 흔히 들어가는
짧은 말은 키워드로 쓰지 않는다. 키워드를 바꾸면 python -m app.scripts.backfill_archive --retheme 으로 다시 매긴다.
"""

import logging
from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crawlers.base import RawFair
from app.crawlers.normalize import PeriodParseError, parse_period
from app.models import FairArchive

logger = logging.getLogger(__name__)

OTHER = "기타"  # 어느 키워드에도 안 맞음
MOVE_IN = "입주박람회"  # 새 아파트 입주민 대상 행사
NOT_FAIR = "박람회 아님"  # 선거 개표, 공연, 면세점 행사, 시험, 공사 기간 등
B2B = "산업·학술"

_NOT_FAIR_WORDS = (
    # 선거·시험·회의
    "개표", "선거", "면접", "정기총회", "시무식", "기념행사", "오찬", "모의고사", "수험생", "청약", "공공디자인",
    "경영분석", "현물심사", "공모", "여호와",
    # 공연·스포츠 경기
    "콘서트", "concert", "뮤지컬", "씨어터", "연극", "오페라", "공연", "놀이극", "팬파티",
    "플래시몹", "버스킹", "k-pop광장", "뮤직페스티벌", "k-music", "힙합", "시네마",
    "주짓수", "배드민턴", "하이록스", "체육대회", "전국체전",
    # 상업 시설 행사·홍보
    "면세점", "백화점", "프로모션", "할인혜택", "인터컨티넨탈", "아쿠아리움", "런칭", "언팩", "프리미어",
    "샘플링", "팝업", "캠페인", "이벤트", "ci교체", "코엑스아이콘", "코엑스윈터", "코엑스하트",
    "coexheart", "urbanpark", "코엑스아트프로젝트",
    # 거리 축제·봉사·기타
    "강남페스티벌", "문화한마당", "축제한마당", "정월대보름", "자원봉사", "봉사", "패킹", "유지보수", "공사기간",
)  # fmt: skip

_B2B_FIRST_WORDS = ("b2b", "수주", "상담회", "소싱", "학술", "학회", "심포지엄", "컨퍼런스", "콘퍼런스", "세미나")

# 일반인 주제 (화면에 이 순서로 보인다)
_CONSUMER_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("베이비·육아", ("베이비", "베페", "유아", "육아", "임신", "출산", "키즈", "어린이박람회")),
    ("웨딩", ("웨딩", "혼수", "결혼", "웨덱스", "신혼")),
    ("취업·창업", (
        "취업", "채용", "일자리", "잡페스티벌", "잡마켓", "잡매칭", "job", "탤런트", "talent", "인재매칭", "일잘러",
        "창업", "프랜차이즈", "스타트업", "startup", "넥스트라이즈", "컴업", "comeup", "데모데이", "유스프러너",
        "해커톤", "hackers", "개원", "사장님", "귀농", "여성up",
    )),
    ("반려동물", ("펫", "캣", "도그", "반려", "애견", "고양이", "강아지", "애완", "렙타일", "파충류", "곤충")),
    ("식음료", (
        "커피", "카페", "푸드", "food", "음식", "식품", "먹거리", "미식", "고메", "디저트", "베이커리", "쇼콜라",
        "주류", "와인", "맥주", "beer", "위스키", "사케", "스피릿", "막걸리", "전통주",
        "차문화", "명차", "茶", "k-tea", "월드티아트", "티&크래프트", "발효", "식초", "김치", "김장",
        "간편식", "hmr", "외식", "급식", "밥상", "미트", "한돈", "pork", "축산박람회", "치킨",
        "비건", "베지", "할랄", "스트로베리", "과일", "농특산", "농수산", "농산물", "특산", "소금",
    )),
    ("캠핑·레저", (
        "캠핑", "camping", "캠페어", "캠피크", "레저", "아웃도어", "낚시", "골프", "자전거", "스포츠", "sports",
        "클래식카",
    )),
    ("여행", ("여행", "관광", "트래블", "travel", "마이스")),
    ("교육·유학", (
        "교육", "에듀", "입학", "진학", "진로", "수시", "정시", "대학", "학교", "교실", "유학", "어학", "이민",
        "올림피아드", "일학습", "도제",
    )),
    ("건축·인테리어", (
        "건축", "인테리어", "리빙", "가구", "하우징", "데코", "메종", "공간디자인", "diy", "리폼", "조경", "정원",
        "목재", "코리아빌드", "꽃박람회",
    )),
    ("재테크·부동산", (
        "재테크", "머니", "금융", "핀테크", "파이낸셜", "경제생활", "부동산", "집코노미", "집노코미", "리얼티",
    )),
    ("뷰티·건강", (
        "뷰티", "beauty", "화장품", "코스메", "코스모", "네일", "nail", "미용", "에스테틱", "스파",
        "건강", "헬스", "웰니스", "wellness", "웰에이징", "다이어트", "수면", "꿀잠", "슬립", "명상", "한방",
        "시니어", "노후", "100세", "재활", "복지", "치매", "dementia",
    )),
    ("쇼핑·생활", (
        "선물전", "선물박람회", "gift", "세일", "sale", "할인전", "직거래", "바자", "메가쇼", "밀리언쇼",
        "millionshow", "수입상품", "수입박람회", "라이프스타일", "주얼리", "액세서리", "한복", "패션",
        "크리스마스페어", "리퍼브", "대구경북박람회", "아이웨어", "p.o.s.e",
    )),
    ("문화·취미", (
        "코믹", "게임", "게이머", "닌텐도", "nintendo", "발로란트", "카트라이더", "스타레일", "플래툰",
        "미술", "예술", "아트페어", "artfair", "아트쇼", "아트페스타", "artfesta", "artono", "bankart",
        "아트대구", "아트아시아", "아트엑스포", "월드아트", "조형아트", "프리즈", "조각", "사진",
        "디자인페스티벌", "디자인위크", "디자인코리아", "일러스트", "일러스타", "웹툰", "애니", "캐릭터",
        "굿즈", "피규어", "프라모델", "인형", "돌프리마켓", "솜프리마켓", "collectibles", "하비", "그래비트랙스",
        "키보드", "문구", "핸드메이드", "핸드아티", "공예", "크래프트", "퀼트", "도서",
        "콘텐츠", "팝컬처", "팝컬쳐", "크리에이터", "1인미디어", "불교", "반다이", "포켓몬",
        "어반브레이크", "contemporart",
    )),
)  # fmt: skip

_B2B_WORDS = (
    "산업", "기술", "기계", "자동화", "소재", "부품", "철강", "섬유", "프리뷰인서울", "농기계", "농기자재",
    "전기", "전력", "전자", "전파", "반도체", "세미콘", "디스플레이", "배터리", "에너지", "수소", "태양광",
    "원자력", "원전생태계", "가스", "그린", "환경", "물주간", "물총회", "공기", "미세먼지", "바이러스",
    "로봇", "로보", "인공지능", "사물인터넷", "테크", "science", "ieee", "siggraph",
    "aiot", "ai서밋", "aifesta", "it쇼", "ict", "소프트웨어", "소프트웨이브",
    "디지털", "메타버스", "kme", "vr", "브이알", "증강현실", "블록체인", "스마트", "시큐", "보안",
    "모빌리티", "자동차", "ev트렌드", "xev", "무인", "드론", "공항", "물류", "유통", "이커머스", "구독",
    "방송", "음향", "조명", "koba", "kosound",
    "의료", "의학", "병원", "메디", "치과", "제약", "바이오", "라이프사이언스", "cphi", "약사", "팜엑스포",
    "인터참", "안경", "소방", "안전", "청소", "위생",
    "발명", "특허", "상표", "사인디자인", "수출", "무역", "마케팅", "호텔쇼", "호텔페어", "숙박", "국토",
    "해양수산", "조달", "국방", "혁신", "기업", "비즈니스", "전시산업", "전시컨벤션", "사회적경제",
    "사회적가치", "esg", "소셜임팩트", "미래", "융합", "산학연", "산림", "measuring", "일렉스", "kdtex",
    "경제학자",
)  # fmt: skip

RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (MOVE_IN, ("입주",)),
    (B2B, _B2B_FIRST_WORDS),
    (NOT_FAIR, _NOT_FAIR_WORDS),
    *_CONSUMER_RULES,
    (B2B, _B2B_WORDS),
)

THEMES: tuple[str, ...] = (*(name for name, _ in _CONSUMER_RULES), B2B)  # 통계에 보이는 주제 (이 순서)
EXCLUDED: tuple[str, ...] = (MOVE_IN, NOT_FAIR)  # 박람회가 아니라 통계에서 빼는 것


def _normalize(text: str) -> str:
    return "".join(text.casefold().split())


def theme_of(title: str) -> str:
    text = _normalize(title)
    for theme, words in RULES:
        if any(w in text for w in words):
            return theme
    return OTHER


def upsert(db: Session, *, source: str, venue_id: int, items: Iterable[RawFair], now: datetime) -> dict[str, int]:
    """같은 (source, external_id) 는 덮어쓴다. 기간을 못 읽는 항목은 건너뛴다."""
    counts = {"saved": 0, "skipped": 0}
    # 원본 표에 같은 행사가 두 줄로 적힌 경우가 있다 (엑스코 2019 웨딩박람회). 묶음 안에서 먼저 하나로 합친다
    unique = {raw.external_id[:255]: raw for raw in items}
    for raw in unique.values():
        try:
            start, end = parse_period(raw.period_text)
        except PeriodParseError:
            logger.warning("archive: period parse failed %r", raw.period_text)
            counts["skipped"] += 1
            continue
        row = db.scalar(
            select(FairArchive).where(FairArchive.source == source, FairArchive.external_id == raw.external_id)
        )
        if row is None:
            row = FairArchive(source=source, external_id=raw.external_id[:255])
            db.add(row)
        row.venue_id = venue_id
        row.title = raw.title[:300]
        row.start_date, row.end_date = start, end
        row.theme = theme_of(raw.title)
        row.collected_at = now
        counts["saved"] += 1
    db.flush()
    return counts


def retheme(db: Session) -> int:
    changed = 0
    for row in db.scalars(select(FairArchive)):
        theme = theme_of(row.title)
        if theme != row.theme:
            row.theme = theme
            changed += 1
    db.flush()
    return changed
