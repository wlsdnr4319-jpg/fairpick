from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.fair import Fair


class Venue(TimestampMixin, Base):
    __tablename__ = "venues"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)  # 예: 코엑스
    region: Mapped[str] = mapped_column(String(20))  # 시·도. 목록 필터(region=서울)
    address: Mapped[str | None] = mapped_column(String(255))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))  # 3단계 지도
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    parking_note: Mapped[str | None] = mapped_column(String(500))

    aliases: Mapped[list["VenueAlias"]] = relationship(
        back_populates="venue", cascade="all, delete-orphan", passive_deletes=True
    )
    fairs: Mapped[list["Fair"]] = relationship(back_populates="venue")


class VenueAlias(Base):
    """수집한 장소 문자열("COEX", "서울 코엑스")을 전시장으로 맞추는 별칭 (레퍼런스 8장 정규화 규칙)."""

    __tablename__ = "venue_aliases"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id", ondelete="CASCADE"))
    alias: Mapped[str] = mapped_column(String(100), unique=True)

    venue: Mapped[Venue] = relationship(back_populates="aliases")
