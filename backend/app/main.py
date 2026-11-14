"""
페어픽(FairPick) API 서버.

실행 (backend/ 폴더에서):
    .venv\\Scripts\\activate
    uvicorn app.main:app --reload --port 8000

API 문서: http://localhost:8000/docs
"""

import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.routers import admin, admin_crawl, auth, engagement, fairs, health, me, oauth, push, refs, stats, uploads

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
request_logger = logging.getLogger("app.request")

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="FairPick API",
        version="0.1.0",
        description="페어픽: 일반인이 즐길 수 있는 박람회 큐레이션 서비스",
    )

    # 배포에서는 Nginx 가 프론트와 API 를 한 도메인으로 묶어 CORS 가 필요 없다 (레퍼런스 14장).
    # 개발 중 Vite 프록시 없이 직접 부를 때를 위해 허용 목록만 열어 둔다.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    # 요청 로그: 경로, 상태 코드, 소요 시간 (레퍼런스 14장). 쿼리스트링·본문·토큰은 남기지 않는다
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        if request.url.path != f"{API_PREFIX}/health":
            request_logger.info(
                "%s %s %s %.0fms",
                request.method,
                request.url.path,
                response.status_code,
                (time.perf_counter() - start) * 1000,
            )
        return response

    app.include_router(health.router, prefix=API_PREFIX)
    # engagement 는 /fairs/calendar 가 /fairs/{fair_id} 보다 먼저 잡히도록 fairs 보다 앞에 둔다
    for module in (auth, oauth, me, push, engagement, fairs, refs, stats, admin, admin_crawl, uploads):
        app.include_router(module.router, prefix=API_PREFIX)

    return app


app = create_app()
