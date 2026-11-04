# 페어픽 (FairPick)

일반인이 즐길 수 있는 식음료·문화·이색 박람회를 한곳에 모으고, 관람 조건과 사전등록 마감까지 알려주는 웹 서비스입니다.

> 개발 중 — 1주차: 설계와 환경. 8주차에 MVP를 배포할 예정입니다.

## 왜 만드나

- 박람회 일정이 코엑스, 킨텍스, aT센터, 벡스코 등 전시장 사이트마다 흩어져 있습니다.
- 업계 종사자 대상(B2B) 행사인지, 일반인도 입장할 수 있는지 한눈에 알기 어렵습니다.
- 사전등록하면 무료나 할인인 행사가 있지만, 마감일을 놓치기 쉽습니다.

## 기술 스택

| 영역 | 선택 |
| --- | --- |
| 프론트엔드 | React + Vite, React Router, TanStack Query, Tailwind CSS |
| 백엔드 | FastAPI, SQLAlchemy 2.0 + Alembic, Pydantic |
| DB | MySQL 8 (Docker) |
| 인증 | PyJWT + pwdlib(Argon2) |
| 수집 | httpx + BeautifulSoup, APScheduler |
| 인프라 | Docker Compose, Nginx |

## 저장소 구조

```
fairpick/
├── backend/            FastAPI 앱 (app/), 테스트 (tests/)
├── frontend/           React + Vite
├── docs/               ERD, 테이블 SQL
└── docker-compose.yml  로컬 개발용 MySQL
```

## 로컬 실행

준비물: Python 3.12+, Node.js 20+, Docker Desktop

```powershell
# 0. 환경 변수
copy .env.example .env        # 값 채우기

# 1. DB (호스트 포트 3308. 3306 은 로컬 MySQL 과 겹치기 쉬워 피했다)
docker compose up -d db

# 2. 백엔드 (터미널 1)
cd backend
py -3.13 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head          # 테이블 만들기
python -m app.scripts.seed    # 카테고리·태그·전시장·박람회 30건 (여러 번 실행해도 됨)
uvicorn app.main:app --reload --port 8000
# API 문서: http://localhost:8000/docs

# 3. 프론트엔드 (터미널 2)
cd frontend
npm install
npm run dev
# http://localhost:5173  (/api 요청은 백엔드로 프록시)
```

테스트: `cd backend` 후 `pytest`, 린트: `ruff check .`

- 테스트는 SQLite 가 아니라 Docker MySQL 의 `fairpick_test` DB 에서 돈다. 매 실행마다 마이그레이션으로 다시 만들고, 테스트마다 롤백한다.
- `fairpick_test` 는 MySQL 컨테이너를 처음 만들 때 `docker/mysql-init` 스크립트가 만든다.

## API (현재)

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| GET | `/api/v1/health` | 서버 상태 (`?db=true` 면 DB 연결까지 확인) |
| GET | `/api/v1/fairs` | 공개 박람회 목록, 개막순, `page`·`size`(최대 50) |
| GET | `/api/v1/fairs/{fair_id}` | 박람회 상세. 비공개·없는 박람회는 404 `FAIR_NOT_FOUND` |

진행 상태(`progress`)와 D-day 는 DB 에 저장하지 않고, 조회할 때 한국 시간 기준 오늘 날짜로 계산한다.

## 문서

- [ERD](docs/erd.md)
- [1단계 테이블 SQL](docs/schema.sql)
