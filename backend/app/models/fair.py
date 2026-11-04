from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.bookmark import Bookmark
    from app.models.category import Category
    from app.models.tag import FairTag
    from app.models.venue import Venue

PUBLIC_ACCESS = ("public", "partial", "trade_only", "unknown")
FAIR_STATUS = ("draft", "published", "hidden")
FAIR_SOURCE = ("manual", "crawler", "api")


class Fair(TimestampMixin, Base):
    """
    박람회 (레퍼런스 6장 fairs 상세).

    진행 상태(예정·진행 중·종료)와 D-day 는 저장하지 않고 조회할 때 날짜로 계산한다.
    박람회는 지우지 않고 status = 'hidden' 으로 숨긴다.
    """

    __tablename__ = "fairs"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_fairs_period"),
        CheckConstraint("price_onsite IS NULL OR price_onsite >= 0", name="ck_fairs_price_onsite"),
        CheckConstraint("price_prereg IS NULL OR price_prereg >= 0", name="ck_fairs_price_prereg"),
        Index("ix_fairs_status_start", "status", "start_date"),
        Index("ix_fairs_status_end", "status", "end_date"),
        Index("ix_fairs_category_start", "category_id", "start_date"),
        Index("ix_fairs_prereg_end", "prereg_end_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"))
    venue_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("venues.id"))
    hall: Mapped[str | None] = mapped_column(String(100))  # 예: A홀

    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    open_time: Mapped[time | None] = mapped_column(Time)
    close_time: Mapped[time | None] = mapped_column(Time)
    hours_note: Mapped[str | None] = mapped_column(String(255))  # 예: 마지막 날 16시 마감

    public_access: Mapped[str] = mapped_column(
        Enum(*PUBLIC_ACCESS, name="fair_public_access"), default="unknown", server_default="unknown"
    )
    access_note: Mapped[str | None] = mapped_column(String(255))  # 예: 일반인은 주말만 입장

    price_onsite: Mapped[int | None] = mapped_column(Integer)  # 0 = 무료, NULL = 미확인
    price_prereg: Mapped[int | None] = mapped_column(Integer)  # 0 = 사전등록 시 무료
    prereg_start_at: Mapped[datetime | None] = mapped_column(DateTime)  # UTC
    prereg_end_at: Mapped[datetime | None] = mapped_column(DateTime)  # UTC, 마감 임박·알림 기준
    prereg_url: Mapped[str | None] = mapped_column(String(500))
    official_url: Mapped[str | None] = mapped_column(String(500))

    summary: Mapped[str | None] = mapped_column(Text)  # 관리자가 직접 쓴 소개 (원문 복제 금지)
    visit_tip: Mapped[str | None] = mapped_column(Text)  # 주차, 붐비는 시간, 추천 동선
    image_url: Mapped[str | None] = mapped_column(String(500))

    status: Mapped[str] = mapped_column(Enum(*FAIR_STATUS, name="fair_status"), default="draft", server_default="draft")
    source: Mapped[str] = mapped_column(Enum(*FAIR_SOURCE, name="fair_source"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime)  # 정보 확인일

    category: Mapped["Category"] = relationship(back_populates="fairs")
    venue: Mapped["Venue"] = relationship(back_populates="fairs")
    fair_tags: Mapped[list["FairTag"]] = relationship(back_populates="fair", cascade="all, delete-orphan")
    bookmarks: Mapped[list["Bookmark"]] = relationship(back_populates="fair")
