from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CHAR, BigInteger, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, utcnow

if TYPE_CHECKING:
    from app.models.bookmark import Bookmark


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))  # Argon2 (pwdlib)
    nickname: Mapped[str] = mapped_column(String(30))
    role: Mapped[str] = mapped_column(
        Enum("user", "admin", name="user_role"), default="user", server_default="user"
    )

    # 탈퇴하면 토큰·북마크를 함께 지운다 (DB 의 ON DELETE CASCADE 와 맞춘다)
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    bookmarks: Mapped[list["Bookmark"]] = relationship(
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

    user: Mapped[User] = relationship(back_populates="refresh_tokens")
