"""
비밀번호 해시와 토큰 (레퍼런스 10장 인증과 보안).

- 비밀번호: pwdlib 의 Argon2 로 해시만 저장한다.
- 액세스 토큰: PyJWT(HS256), 30분. 브라우저 메모리에만 둔다.
- 리프레시 토큰: 추측할 수 없는 무작위 문자열, 14일. httpOnly 쿠키로 주고 DB 에는 SHA-256 해시만 저장한다.
  쓸 때마다 새로 발급하고 이전 토큰은 폐기한다(회전).
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.core.errors import AppError

_password_hash = PasswordHash.recommended()  # Argon2
_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _password_hash.verify(password, hashed)


# 로그인 실패 시에도 해시 비교 시간을 비슷하게 맞춰, 가입된 이메일인지 응답 시간으로 알아내지 못하게 한다
DUMMY_PASSWORD_HASH = _password_hash.hash("dummy-password-for-timing")


def create_access_token(user_id: int, role: str, now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=get_settings().access_token_minutes),
    }
    return jwt.encode(payload, get_settings().jwt_secret, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError:
        # 프론트는 이 code 를 받으면 /auth/refresh 후 원래 요청을 다시 보낸다
        raise AppError(401, "TOKEN_EXPIRED", "로그인이 만료됐어요") from None
    except jwt.InvalidTokenError:
        raise AppError(401, "INVALID_TOKEN", "로그인 정보가 올바르지 않아요") from None
    if payload.get("type") != "access":
        raise AppError(401, "INVALID_TOKEN", "로그인 정보가 올바르지 않아요")
    return payload


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
