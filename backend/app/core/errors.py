"""
공통 에러 응답 (레퍼런스 7장 공통 규칙).

모든 에러는 아래 형태로 통일한다. 프론트는 code 로 분기하고 message 를 그대로 보여준다.
    { "error": { "code": "FAIR_NOT_FOUND", "message": "박람회를 찾을 수 없어요" } }

FastAPI 기본 422, 404, 405 응답과 예상 못 한 500 도 같은 형태로 바꾼다.
500 은 원인을 응답에 담지 않고 서버 로그에만 남긴다.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """라우터·서비스 어디서든 raise 하면 공통 에러 형식으로 응답한다."""

    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


# FastAPI/Starlette 가 직접 내는 HTTP 에러의 code·message
_HTTP_ERRORS: dict[int, tuple[str, str]] = {
    400: ("BAD_REQUEST", "잘못된 요청이에요"),
    401: ("UNAUTHORIZED", "로그인이 필요해요"),
    403: ("FORBIDDEN", "접근 권한이 없어요"),
    404: ("NOT_FOUND", "요청한 주소를 찾을 수 없어요"),
    405: ("METHOD_NOT_ALLOWED", "허용되지 않은 요청 방식이에요"),
}


async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message))


async def _http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code, message = _HTTP_ERRORS.get(exc.status_code, (f"HTTP_{exc.status_code}", "요청을 처리할 수 없어요"))
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(code, message),
        headers=getattr(exc, "headers", None),
    )


async def _validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # 어느 필드가 틀렸는지 message 에 붙여 준다. 예: "요청 형식이 올바르지 않아요 (email)"
    fields = []
    for err in exc.errors():
        loc = [str(p) for p in err.get("loc", ()) if p not in ("body", "query", "path")]
        if loc:
            fields.append(".".join(loc))
    message = "요청 형식이 올바르지 않아요"
    if fields:
        message += f" ({', '.join(dict.fromkeys(fields))})"
    return JSONResponse(status_code=422, content=error_body("VALIDATION_ERROR", message))


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_body("INTERNAL_ERROR", "일시적인 오류가 발생했어요. 잠시 후 다시 시도해 주세요"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)
