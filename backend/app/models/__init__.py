"""모든 모델을 여기서 import 해 Base.metadata 에 등록한다. Alembic autogenerate 가 이 목록을 본다."""

from app.models.bookmark import Bookmark
from app.models.category import Category
from app.models.crawl import CrawledItem, CrawlRun, CrawlSource
from app.models.fair import Fair
from app.models.tag import FairTag, Tag
from app.models.user import RefreshToken, User
from app.models.venue import Venue, VenueAlias

__all__ = [
    "Bookmark",
    "Category",
    "CrawlRun",
    "CrawlSource",
    "CrawledItem",
    "Fair",
    "FairTag",
    "RefreshToken",
    "Tag",
    "User",
    "Venue",
    "VenueAlias",
]
