"""FastAPI 기본 에러도 { "error": { code, message } } 형태로 나가는지 확인한다 (레퍼런스 7장)."""

from fastapi import APIRouter

from app.core.errors import AppError


def test_unknown_path_is_not_found(client):
    res = client.get("/api/v1/no-such-path")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


def test_wrong_method(client):
    res = client.post("/api/v1/health")
    assert res.status_code == 405
    assert res.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_validation_error_names_the_field(client):
    res = client.get("/api/v1/health?db=not-a-bool")
    assert res.status_code == 422
    body = res.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert "db" in body["message"]


def test_app_error_and_unhandled_error(app, client):
    router = APIRouter()

    @router.get("/_test/app-error")
    def app_error():
        raise AppError(404, "FAIR_NOT_FOUND", "박람회를 찾을 수 없어요")

    @router.get("/_test/boom")
    def boom():
        raise RuntimeError("secret internal detail")

    app.include_router(router)

    res = client.get("/_test/app-error")
    assert res.status_code == 404
    assert res.json() == {"error": {"code": "FAIR_NOT_FOUND", "message": "박람회를 찾을 수 없어요"}}

    res = client.get("/_test/boom")
    assert res.status_code == 500
    assert res.json()["error"]["code"] == "INTERNAL_ERROR"
    # 500 응답에 내부 원인을 담지 않는다 (레퍼런스 10장 보안 체크리스트)
    assert "secret" not in res.text
