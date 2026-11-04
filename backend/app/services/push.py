"""
웹 푸시 (브라우저 알림, Web Push + VAPID).

브라우저가 구독하면 푸시 서비스(크롬은 FCM, 파이어폭스는 Mozilla, 사파리는 Apple)의 endpoint 주소와
암호화용 키(p256dh, auth)를 준다. 서버는 메시지를 그 키로 암호화하고 VAPID 키로 서명해 endpoint 로 보낸다.

- endpoint 는 사용자가 보내는 값이라, 아무 주소나 받으면 서버가 내부망 주소로 요청을 보내게 만들 수 있다(SSRF).
  그래서 알려진 푸시 서비스 도메인(https)만 받는다.
- 푸시 서비스가 404/410 을 주면 구독이 끝난 것(브라우저에서 알림 차단·데이터 삭제)이라 행을 지운다.
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit

from pywebpush import WebPushException, webpush
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import PushSubscription

logger = logging.getLogger(__name__)

# 브라우저별 푸시 서비스 도메인 (정확히 같거나 하위 도메인)
ALLOWED_PUSH_HOSTS = (
    "fcm.googleapis.com",  # Chrome, Edge(일부), Android
    "updates.push.services.mozilla.com",  # Firefox
    "notify.windows.com",  # Edge (WNS)
    "push.apple.com",  # Safari (web.push.apple.com)
)
TTL_SECONDS = 24 * 3600  # 기기가 꺼져 있으면 푸시 서비스가 하루까지 보관


class PushNotConfigured(Exception):
    pass


def is_configured() -> bool:
    s = get_settings()
    return bool(s.vapid_public_key and s.vapid_private_key)


def endpoint_allowed(endpoint: str) -> bool:
    parts = urlsplit(endpoint)
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or not host:
        return False
    return any(host == h or host.endswith("." + h) for h in ALLOWED_PUSH_HOSTS)


def endpoint_hash(endpoint: str) -> str:
    return hashlib.sha256(endpoint.encode()).hexdigest()


def subscribe(
    db: Session, *, user_id: int, endpoint: str, p256dh: str, auth: str, user_agent: str | None, now: datetime
) -> PushSubscription:
    """같은 브라우저가 다시 구독하면 키를 갱신한다. 다른 계정으로 로그인한 같은 브라우저면 지금 계정으로 옮긴다."""
    digest = endpoint_hash(endpoint)
    sub = db.scalar(select(PushSubscription).where(PushSubscription.endpoint_hash == digest))
    if sub is None:
        sub = PushSubscription(endpoint=endpoint, endpoint_hash=digest, created_at=now)
        db.add(sub)
    sub.user_id = user_id
    sub.p256dh, sub.auth = p256dh, auth
    sub.user_agent = (user_agent or "")[:300] or None
    db.flush()
    return sub


def unsubscribe(db: Session, *, user_id: int, endpoint: str) -> bool:
    sub = db.scalar(
        select(PushSubscription).where(
            PushSubscription.endpoint_hash == endpoint_hash(endpoint), PushSubscription.user_id == user_id
        )
    )
    if sub is None:
        return False
    db.delete(sub)
    db.flush()
    return True


@dataclass
class DeliveryResult:
    delivered: int = 0
    gone: int = 0  # 끝난 구독 (지웠다)
    failed: int = 0  # 일시 오류 (다음에 다시)


def send_to_user(db: Session, user_id: int, payload: dict, *, now: datetime) -> DeliveryResult:
    """사용자의 모든 기기로 보낸다. 끝난 구독은 지운다."""
    if not is_configured():
        raise PushNotConfigured
    result = DeliveryResult()
    subs = db.scalars(select(PushSubscription).where(PushSubscription.user_id == user_id)).all()
    for sub in subs:
        status = _send_one(sub, payload)
        if status == "ok":
            sub.last_success_at = now
            result.delivered += 1
        elif status == "gone":
            db.delete(sub)
            result.gone += 1
        else:
            result.failed += 1
    db.flush()
    return result


def _send_one(sub: PushSubscription, payload: dict) -> str:
    if not endpoint_allowed(sub.endpoint):  # 저장 전에 거르지만, 규칙이 바뀐 경우를 대비해 보내기 전에도 확인
        return "gone"
    s = get_settings()
    try:
        webpush(
            subscription_info={"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}},
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=s.vapid_private_key,
            vapid_claims={"sub": s.vapid_subject},
            ttl=TTL_SECONDS,
            timeout=10,
        )
        return "ok"
    except WebPushException as exc:
        code = exc.response.status_code if exc.response is not None else None
        if code in (404, 410):
            return "gone"
        logger.warning("push failed (%s) %s: %s", code, urlsplit(sub.endpoint).hostname, exc)
        return "error"
    except Exception:  # 네트워크 오류 등
        logger.exception("push failed: %s", urlsplit(sub.endpoint).hostname)
        return "error"
