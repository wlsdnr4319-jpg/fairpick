"""
2단계 테이블 (레퍼런스 6장 테이블 목록).
visits, tag_votes, notifications 도 bookmarks 처럼 users 와 fairs 사이에 놓인다.
회원 탈퇴 시 관람 노트·알림 등은 ON DELETE CASCADE 로 함께 지운다.
"""

from datetime import date, datetime

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    false,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, utcnow

NOTIFICATION_TYPES = ("prereg_deadline", "opening_soon", "fair_updated")


class Visit(TimestampMixin, Base):
    """관람 노트·후기. 공개(is_public)한 노트는 상세 페이지의 후기로 보인다."""

    __tablename__ = "visits"
    __table_args__ = (
        UniqueConstraint("user_id", "fair_id", name="uq_visits_user_fair"),
        CheckConstraint("rating IS NULL OR (rating BETWEEN 1 AND 5)", name="ck_visits_rating"),
        Index("ix_visits_fair_public", "fair_id", "is_public"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    fair_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fairs.id"))
    visited_on: Mapped[date | None] = mapped_column(Date)
    rating: Mapped[int | None] = mapped_column(SmallInteger)
    memo: Mapped[str | None] = mapped_column(Text)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())

    user = relationship("User")
    fair = relationship("Fair")
    likes: Mapped[list["VisitLike"]] = relationship(cascade="all, delete-orphan", passive_deletes=True)


class VisitLike(Base):
    __tablename__ = "visit_likes"
    __table_args__ = (Index("ix_visit_likes_visit", "visit_id"),)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    visit_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("visits.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class TagVote(Base):
    """'데이트 추천' 같은 태그 투표. 3표 이상이면 fair_tags 에 source='vote' 로 반영한다."""

    __tablename__ = "tag_votes"
    __table_args__ = (Index("ix_tag_votes_fair_tag", "fair_id", "tag_id"),)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    fair_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fairs.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class NotificationSetting(Base):
    """알림 종류별 수신 여부. 회원가입 때 기본값으로 함께 만든다."""

    __tablename__ = "notification_settings"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    prereg_deadline: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    opening_soon: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    fair_updated: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    # 로그인 없이 누르는 수신 거부 링크용
    unsubscribe_token: Mapped[str] = mapped_column(String(64), unique=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Notification(Base):
    """알림 발송 큐. UNIQUE(user_id, fair_id, type, ref_key, channel) 가 같은 알림의 중복 발송을 막는다."""

    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("user_id", "fair_id", "type", "ref_key", "channel", name="uq_notifications_dedupe"),
        Index("ix_notifications_status_scheduled", "status", "scheduled_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    fair_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fairs.id"))
    type: Mapped[str] = mapped_column(Enum(*NOTIFICATION_TYPES, name="notification_type"))
    ref_key: Mapped[str] = mapped_column(String(50))  # 같은 종류 안의 회차 구분: 마감 일시, 시작일, 변경 로그 ID
    channel: Mapped[str] = mapped_column(
        Enum("email", "push", name="notification_channel"), default="email", server_default="email"
    )
    status: Mapped[str] = mapped_column(
        Enum("pending", "sent", "failed", "skipped", name="notification_status"),
        default="pending",
        server_default="pending",
    )
    attempts: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    scheduled_at: Mapped[datetime] = mapped_column(DateTime)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)

    user = relationship("User")
    fair = relationship("Fair")


class PushSubscription(Base):
    """
    브라우저 푸시 구독. 기기(브라우저)마다 하나. endpoint 는 푸시 서비스(FCM, Mozilla 등)가 준 주소다.
    endpoint 가 길어(수백 자) UNIQUE 인덱스를 걸기 어려우므로 SHA-256 해시에 UNIQUE 를 건다.
    """

    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    endpoint: Mapped[str] = mapped_column(Text)
    endpoint_hash: Mapped[str] = mapped_column(CHAR(64), unique=True)
    p256dh: Mapped[str] = mapped_column(String(200))  # 브라우저 공개 키 (메시지 암호화용)
    auth: Mapped[str] = mapped_column(String(100))  # 브라우저 인증 비밀값
    user_agent: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime)


class FairChangeLog(Base):
    """박람회 변경 이력. 북마크한 사람에게 '정보 변경' 알림을 보낼 때 쓴다."""

    __tablename__ = "fair_change_logs"
    __table_args__ = (Index("ix_fair_change_logs_created", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    fair_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fairs.id"))
    field_name: Mapped[str] = mapped_column(String(50))
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    changed_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PasswordResetToken(Base):
    """비밀번호 재설정 토큰. 30분 유효, 1회용, 해시로 저장한다 (레퍼런스 10장)."""

    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(CHAR(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
