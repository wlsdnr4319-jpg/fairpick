"""모든 모델을 여기서 import 해 Base.metadata 에 등록한다. Alembic autogenerate 가 이 목록을 본다."""

from app.models.bookmark import Bookmark
from app.models.category import Category
from app.models.crawl import CrawledItem, CrawlRun, CrawlSource
from app.models.engagement import (
    FairChangeLog,
    Notification,
    NotificationSetting,
    PasswordResetToken,
    TagVote,
    Visit,
    VisitLike,
)
from app.models.fair import Fair
from app.models.login_attempt import LoginAttempt
from app.models.tag import FairTag, Tag
from app.models.user import RefreshToken, SocialAccount, User
from app.models.venue import Venue, VenueAlias

__all__ = [
    "Bookmark",
    "Category",
    "CrawlRun",
    "CrawlSource",
    "CrawledItem",
    "Fair",
    "FairChangeLog",
    "LoginAttempt",
    "Notification",
    "NotificationSetting",
    "PasswordResetToken",
    "TagVote",
    "Visit",
    "VisitLike",
    "FairTag",
    "RefreshToken",
    "SocialAccount",
    "Tag",
    "User",
    "Venue",
    "VenueAlias",
]
