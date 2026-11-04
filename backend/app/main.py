"""
페어픽(FairPick) API 서버.

실행 (backend/ 폴더에서):
    .venv\\Scripts\\activate
    uvicorn app.main:app --reload --port 8000

API 문서: http://localhost:8000/docs
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.routers import fairs, health

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

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

    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(fairs.router, prefix=API_PREFIX)

    return app


app = create_app()
