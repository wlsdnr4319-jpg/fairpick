from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import utcnow

if TYPE_CHECKING:
    from app.models.fair import Fair
    from app.models.user import User


class Bookmark(Base):
    """PK(user_id, fair_id) 덕분에 같은 박람회를 두 번 북마크해도 1건이다 (PUT 멱등성)."""

    __tablename__ = "bookmarks"
    __table_args__ = (Index("ix_bookmarks_fair", "fair_id"),)

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    fair_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fairs.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped["User"] = relationship(back_populates="bookmarks")
    fair: Mapped["Fair"] = relationship(back_populates="bookmarks")
