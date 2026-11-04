"""수집 파이프라인 테이블 (레퍼런스 8장). 수집 결과는 검수 큐(crawled_items)에 쌓인 뒤 관리자가 승인한다."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    CHAR,
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, utcnow


class CrawlSource(TimestampMixin, Base):
    __tablename__ = "crawl_sources"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    venue_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("venues.id"))
    parser_key: Mapped[str] = mapped_column(String(50), unique=True)  # 파서 등록 키. 예: coex
    list_url: Mapped[str] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    policy_checked_at: Mapped[datetime | None] = mapped_column(DateTime)  # robots.txt·약관 확인 일시
    policy_note: Mapped[str | None] = mapped_column(String(500))

    runs: Mapped[list["CrawlRun"]] = relationship(back_populates="source")
    items: Mapped[list["CrawledItem"]] = relationship(back_populates="source")


class CrawlRun(Base):
    __tablename__ = "crawl_runs"
    __table_args__ = (Index("ix_crawl_runs_source_started", "source_id", "started_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("crawl_sources.id"))
    status: Mapped[str] = mapped_column(
        Enum("running", "succeeded", "failed", name="crawl_run_status"),
        default="running",
        server_default="running",
    )
    found_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    new_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    changed_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

    source: Mapped[CrawlSource] = relationship(back_populates="runs")


class CrawledItem(Base):
    __tablename__ = "crawled_items"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_crawled_items_source_external"),
        Index("ix_crawled_items_review", "review_status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("crawl_sources.id"))
    external_id: Mapped[str] = mapped_column(String(255))  # 원본 사이트의 행사 ID 또는 상세 URL
    raw_title: Mapped[str] = mapped_column(String(300))
    raw_period: Mapped[str | None] = mapped_column(String(200))
    raw_venue: Mapped[str | None] = mapped_column(String(200))
    detail_url: Mapped[str | None] = mapped_column(String(500))
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    parsed_start_date: Mapped[date | None] = mapped_column(Date)  # 정규화 실패하면 NULL
    parsed_end_date: Mapped[date | None] = mapped_column(Date)
    parsed_venue_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("venues.id"))
    content_hash: Mapped[str] = mapped_column(CHAR(64))  # 제목·기간·장소 문자열의 SHA-256
    change_status: Mapped[str] = mapped_column(
        Enum("new", "changed", "unchanged", name="crawled_item_change_status")
    )
    review_status: Mapped[str] = mapped_column(
        Enum("pending", "approved", "rejected", "merged", name="crawled_item_review_status"),
        default="pending",
        server_default="pending",
    )
    fair_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fairs.id"))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    source: Mapped[CrawlSource] = relationship(back_populates="items")
