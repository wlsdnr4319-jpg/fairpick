"""
헬스 체크 (레퍼런스 14장 운영 체크리스트, 15장 업타임 모니터링).

GET /api/v1/health          서버가 살아 있는지만 본다. 모니터링은 이것을 5분마다 호출한다.
GET /api/v1/health?db=true  DB 연결까지 확인한다. 배포 직후 점검용.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(
    db: Annotated[Session, Depends(get_db)],
    check_db: Annotated[bool, Query(alias="db")] = False,
):
    if check_db:
        try:
            db.execute(text("SELECT 1"))
        except SQLAlchemyError:
            raise AppError(503, "DB_UNAVAILABLE", "DB에 연결할 수 없어요") from None
        return {"status": "ok", "db": "ok"}
    return {"status": "ok"}
