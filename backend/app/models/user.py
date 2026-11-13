from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CHAR, BigInteger, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, utcnow

if TYPE_CHECKING:
    from app.models.bookmark import Bookmark


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # 소셜 로그인으로 가입했는데 제공자가 확인된 이메일을 주지 않으면 NULL (알림 메일을 보내지 않는다)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    # Argon2 (pwdlib). 소셜 로그인으로만 가입하면 NULL. 비밀번호 재설정으로 나중에 만들 수 있다
    password_hash: Mapped[str | None] = mapped_column(String(255))
    nickname: Mapped[str] = mapped_column(String(30))
    role: Mapped[str] = mapped_column(Enum("user", "admin", name="user_role"), default="user", server_default="user")

    # 탈퇴하면 토큰·북마크를 함께 지운다 (DB 의 ON DELETE CASCADE 와 맞춘다)
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    bookmarks: Mapped[list["Bookmark"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    social_accounts: Mapped[list["SocialAccount"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(CHAR(64), unique=True)  # SHA-256, 원문은 저장하지 않는다
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)  # 회전·로그아웃 시 채운다
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    # 회전으로 이 토큰 대신 발급한 새 토큰. 새 쿠키를 담은 응답이 끊긴 경우(페이지 이동 등)를 가려내는 데 쓴다
    replaced_by_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("refresh_tokens.id", ondelete="SET NULL"))

    user: Mapped[User] = relationship(back_populates="refresh_tokens")


SOCIAL_PROVIDERS = ("kakao", "google")


class SocialAccount(Base):
    """소셜 로그인 연결. 한 회원이 카카오·구글을 모두 연결할 수 있다 (레퍼런스 6장 social_accounts)."""

    __tablename__ = "social_accounts"
    __table_args__ = (UniqueConstraint("provider", "provider_user_id", name="uq_social_accounts_provider_user"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(Enum(*SOCIAL_PROVIDERS, name="social_provider"))
    provider_user_id: Mapped[str] = mapped_column(String(255))  # 카카오 회원번호, 구글 sub
    email: Mapped[str | None] = mapped_column(String(255))  # 연결할 때 제공자가 준 이메일 (참고용)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped[User] = relationship(back_populates="social_accounts")
