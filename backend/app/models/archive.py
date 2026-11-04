from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import utcnow


class FairArchive(Base):
    """
    지난 행사 기록 (분석 전용). 전시장 사이트의 지난 일정을 한 번에 모아 계절별·연도별 추이를 본다.
    서비스 목록·검수 큐(fairs, crawled_items)와 섞지 않는다. 카테고리·입장료 같은 검수 정보가 없기 때문이다.
    theme 은 제목 키워드로 나눈 주제다 (services/archive.py THEMES).
    """

    __tablename__ = "fair_archive"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_fair_archive_source_external"),
        Index("ix_fair_archive_start_date", "start_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source: Mapped[str] = mapped_column(String(30))  # 파서 키: exco, coex, setec
    external_id: Mapped[str] = mapped_column(String(255))
    venue_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("venues.id"))
    title: Mapped[str] = mapped_column(String(300))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    theme: Mapped[str] = mapped_column(String(30))
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
