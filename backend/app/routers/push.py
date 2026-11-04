"""
웹 푸시 구독 API (services/push.py).

GET    /api/v1/push/config                 푸시를 쓸 수 있는지와 공개 키 (브라우저가 구독할 때 쓴다)
POST   /api/v1/me/push-subscriptions       이 기기 구독 등록 (같은 기기면 갱신)
DELETE /api/v1/me/push-subscriptions       이 기기 구독 해제
POST   /api/v1/me/push-subscriptions/test  내 모든 기기로 시험 알림
"""

from typing import Annotated

from fastapi import APIRouter, Header, Response, status
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession, Now
from app.core.errors import AppError
from app.services import push

router = APIRouter(tags=["push"])


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=20, max_length=200)
    auth: str = Field(min_length=8, max_length=100)


class SubscriptionIn(BaseModel):
    # 브라우저 PushSubscription.toJSON() 과 같은 모양
    endpoint: str = Field(min_length=10, max_length=1000)
    keys: PushKeys


class EndpointIn(BaseModel):
    endpoint: str = Field(min_length=10, max_length=1000)


def _require_configured() -> None:
    if not push.is_configured():
        raise AppError(503, "PUSH_NOT_CONFIGURED", "지금은 브라우저 알림을 쓸 수 없어요")


@router.get("/push/config")
def push_config() -> dict:
    enabled = push.is_configured()
    return {"enabled": enabled, "public_key": get_settings().vapid_public_key if enabled else None}


@router.post("/me/push-subscriptions", status_code=status.HTTP_201_CREATED)
def subscribe(
    body: SubscriptionIn,
    user: CurrentUser,
    db: DbSession,
    now: Now,
    user_agent: Annotated[str | None, Header()] = None,
) -> dict:
    _require_configured()
    if not push.endpoint_allowed(body.endpoint):
        # 알려진 푸시 서비스 주소만 받는다 (서버가 임의 주소로 요청하게 만드는 SSRF 방지)
        raise AppError(422, "INVALID_PUSH_ENDPOINT", "지원하지 않는 브라우저 알림 주소예요")
    push.subscribe(
        db,
        user_id=user.id,
        endpoint=body.endpoint,
        p256dh=body.keys.p256dh,
        auth=body.keys.auth,
        user_agent=user_agent,
        now=now,
    )
    db.commit()
    return {"subscribed": True}


@router.delete("/me/push-subscriptions", status_code=status.HTTP_204_NO_CONTENT)
def unsubscribe(body: EndpointIn, user: CurrentUser, db: DbSession) -> Response:
    push.unsubscribe(db, user_id=user.id, endpoint=body.endpoint)  # 없어도 204 (멱등)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/me/push-subscriptions/test")
def send_test(user: CurrentUser, db: DbSession, now: Now) -> dict:
    _require_configured()
    result = push.send_to_user(
        db,
        user.id,
        {"title": "페어픽 알림 테스트", "body": "이 기기에서 알림을 받을 수 있어요", "url": "/mypage/settings"},
        now=now,
    )
    db.commit()
    if result.delivered == 0:
        raise AppError(409, "PUSH_NOT_DELIVERED", "알림을 보내지 못했어요. 브라우저 알림 권한을 확인해 주세요")
    return {"delivered": result.delivered}
