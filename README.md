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

# 1. DB
docker compose up -d db

# 2. 백엔드 (터미널 1)
cd backend
py -3.13 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# API 문서: http://localhost:8000/docs

# 3. 프론트엔드 (터미널 2)
cd frontend
npm install
npm run dev
# http://localhost:5173  (/api 요청은 백엔드로 프록시)
```

테스트: `cd backend` 후 `pytest`, 린트: `ruff check .`

## 문서

- [ERD](docs/erd.md)
- [1단계 테이블 SQL](docs/schema.sql)
