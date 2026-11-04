from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import utcnow

if TYPE_CHECKING:
    from app.models.fair import Fair


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50))  # 예: 데이트 추천
    slug: Mapped[str] = mapped_column(String(50), unique=True)  # 예: date (URL 쿼리 tags=date)
    is_votable: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )  # 사실 정보 태그는 투표 불가

    fair_tags: Mapped[list["FairTag"]] = relationship(
        back_populates="tag", cascade="all, delete-orphan", passive_deletes=True
    )


class FairTag(Base):
    """박람회-태그 연결. source 컬럼이 있어 secondary 대신 연관 객체로 다룬다 (레퍼런스 6장)."""

    __tablename__ = "fair_tags"
    __table_args__ = (Index("ix_fair_tags_tag", "tag_id"),)

    fair_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fairs.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    source: Mapped[str] = mapped_column(
        Enum("admin", "vote", name="fair_tag_source"), default="admin", server_default="admin"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    fair: Mapped["Fair"] = relationship(back_populates="fair_tags")
    tag: Mapped[Tag] = relationship(back_populates="fair_tags")
