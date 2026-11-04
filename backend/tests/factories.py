"""테스트용 데이터 만들기. 필요한 값만 넘기고 나머지는 기본값을 쓴다."""

from datetime import date
from itertools import count

from sqlalchemy.orm import Session

from app.models import Bookmark, Category, Fair, FairTag, Tag, User, Venue

_seq = count(1)


def category(db: Session, code: str = "food", name: str = "식음료") -> Category:
    obj = Category(code=code, name=name)
    db.add(obj)
    db.flush()
    return obj


def venue(db: Session, name: str | None = None, region: str = "서울") -> Venue:
    obj = Venue(name=name or f"전시장{next(_seq)}", region=region)
    db.add(obj)
    db.flush()
    return obj


def tag(db: Session, slug: str, name: str) -> Tag:
    obj = Tag(slug=slug, name=name)
    db.add(obj)
    db.flush()
    return obj


def fair(
    db: Session,
    *,
    category: Category,
    venue: Venue,
    title: str = "테스트 박람회",
    start: date = date(2026, 11, 19),
    end: date = date(2026, 11, 22),
    status: str = "published",
    tags: list[Tag] = (),
    **fields,
) -> Fair:
    obj = Fair(
        title=title,
        category_id=category.id,
        venue_id=venue.id,
        start_date=start,
        end_date=end,
        status=status,
        source="manual",
        **fields,
    )
    db.add(obj)
    db.flush()
    for t in tags:
        db.add(FairTag(fair_id=obj.id, tag_id=t.id))
    db.flush()
    db.expire(obj)  # 관계(fair_tags 등)를 다시 읽게 한다
    return obj


def user(db: Session, email: str | None = None) -> User:
    n = next(_seq)
    obj = User(email=email or f"user{n}@example.com", password_hash="x", nickname=f"user{n}")
    db.add(obj)
    db.flush()
    return obj


def bookmark(db: Session, user: User, fair: Fair) -> Bookmark:
    obj = Bookmark(user_id=user.id, fair_id=fair.id)
    db.add(obj)
    db.flush()
    return obj


def auth_header(user: User) -> dict[str, str]:
    """로그인 과정 없이 바로 쓸 수 있는 액세스 토큰 헤더."""
    from app.core.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


def admin(db: Session) -> User:
    obj = user(db)
    obj.role = "admin"
    db.flush()
    return obj
