"""
알림 선별과 발송 (레퍼런스 9장).

매일 오전 9시(KST)에
  1) 선별: 조건에 맞는 (사용자, 박람회) 조합을 INSERT IGNORE 로 pending 행으로 만든다. 이미 있는 조합은 무시된다.
     사용자가 해당 종류의 알림을 꺼 두었으면 선별 단계에서 뺀다.
  2) 발송: pending 행을 50건씩 메일로 보내고 sent 로 바꾼다. 실패하면 attempts 를 올리고, 3회를 넘기면 failed.
UNIQUE(user_id, fair_id, type, ref_key, channel) 가 같은 알림의 중복 발송을 막는다.
사전등록 마감이 연장되면 ref_key(마감 일시)가 바뀌므로 바뀐 마감에 대한 알림이 한 번 더 나간다.
"""

import logging
import secrets
from datetime import date, datetime, time, timedelta

from sqlalchemy import CHAR, Select, cast, func, insert, literal, select
from sqlalchemy.orm import Session, selectinload

from app.core.timeutil import app_tz, to_local, to_utc_naive
from app.models import Bookmark, Fair, FairChangeLog, Notification, NotificationSetting
from app.services import mail

logger = logging.getLogger(__name__)

BATCH = 50
MAX_ATTEMPTS = 3
# '정보 변경' 알림을 보낼 필드 (기간·장소·사전등록)
NOTIFY_FIELDS = ("start_date", "end_date", "venue_id", "prereg_start_at", "prereg_end_at", "prereg_url")


def ensure_settings(db: Session, user_id: int) -> NotificationSetting:
    s = db.get(NotificationSetting, user_id)
    if s is None:
        s = NotificationSetting(user_id=user_id, unsubscribe_token=secrets.token_urlsafe(32))
        db.add(s)
        db.flush()
    return s


def _kst_day_utc(day: date) -> tuple[datetime, datetime]:
    """한국 시간 하루의 시작·끝을 UTC 로 바꾼 값"""
    start = to_utc_naive(datetime.combine(day, time.min).replace(tzinfo=app_tz()))
    return start, start + timedelta(days=1) - timedelta(microseconds=1)


def _base(setting_flag) -> Select:
    """북마크 × 공개 박람회 × 알림을 켠 사용자"""
    return (
        select(Bookmark.user_id, Fair.id)
        .join(Fair, Fair.id == Bookmark.fair_id)
        .join(NotificationSetting, NotificationSetting.user_id == Bookmark.user_id)
        .where(Fair.status == "published", NotificationSetting.email_enabled.is_(True), setting_flag.is_(True))
    )


def _insert_ignore(db: Session, stmt: Select, columns: list[str]) -> int:
    result = db.execute(insert(Notification).prefix_with("IGNORE").from_select(columns, stmt))
    return result.rowcount or 0


def select_targets(db: Session, *, today: date, now: datetime) -> dict[str, int]:
    cols = ["user_id", "fair_id", "type", "ref_key", "channel", "status", "attempts", "scheduled_at"]
    tail = lambda t, ref: (literal(t), ref, literal("email"), literal("pending"), literal(0), literal(now))  # noqa: E731

    # 사전등록 마감: 마감 전날 (= 마감이 내일 하루 안에 있는 박람회)
    tomorrow_start, tomorrow_end = _kst_day_utc(today + timedelta(days=1))
    prereg = (
        _base(NotificationSetting.prereg_deadline)
        .add_columns(*tail("prereg_deadline", func.date_format(Fair.prereg_end_at, "%Y-%m-%dT%H:%i")))
        .where(Fair.prereg_end_at.between(tomorrow_start, tomorrow_end))
    )
    # 개막 임박: 개막 3일 전
    opening = (
        _base(NotificationSetting.opening_soon)
        .add_columns(*tail("opening_soon", func.date_format(Fair.start_date, "%Y-%m-%d")))
        .where(Fair.start_date == today + timedelta(days=3))
    )
    # 정보 변경: 어제(KST) 관리자가 기간·장소·사전등록 정보를 바꾼 박람회. 박람회당 마지막 변경 로그 ID 를 ref_key 로
    y_start, y_end = _kst_day_utc(today - timedelta(days=1))
    last_change = (
        select(FairChangeLog.fair_id, func.max(FairChangeLog.id).label("log_id"))
        .where(FairChangeLog.created_at.between(y_start, y_end), FairChangeLog.field_name.in_(NOTIFY_FIELDS))
        .group_by(FairChangeLog.fair_id)
        .subquery()
    )
    updated = (
        _base(NotificationSetting.fair_updated)
        .join(last_change, last_change.c.fair_id == Fair.id)
        .add_columns(*tail("fair_updated", cast(last_change.c.log_id, CHAR(50))))
        .where(Fair.end_date >= today)
    )

    counts = {}
    for name, stmt in (("prereg_deadline", prereg), ("opening_soon", opening), ("fair_updated", updated)):
        counts[name] = _insert_ignore(db, stmt, cols)
    db.commit()
    return counts


_HEADLINES = {
    "prereg_deadline": "내일 사전등록이 마감돼요",
    "opening_soon": "3일 뒤 개막해요",
    "fair_updated": "북마크한 박람회 정보가 바뀌었어요",
}


def _period(f: Fair) -> str:
    fmt = lambda d: f"{d.month}.{d.day}"  # noqa: E731
    return fmt(f.start_date) if f.start_date == f.end_date else f"{fmt(f.start_date)} ~ {fmt(f.end_date)}"


def build_mail(n: Notification, setting: NotificationSetting, base_url: str) -> mail.Mail:
    f = n.fair
    detail = None
    if n.type == "prereg_deadline" and f.prereg_end_at:
        local = to_local(f.prereg_end_at)
        detail = f"사전등록 마감: {local.month}.{local.day} {local:%H:%M}"
    if n.type == "fair_updated":
        detail = "기간, 장소 또는 사전등록 정보가 바뀌었어요. 최신 정보를 확인해 주세요."
    return mail.Mail(
        to=n.user.email,
        subject=f"[페어픽] {_HEADLINES[n.type]}: {f.title}",
        template="notification",
        context={
            "headline": _HEADLINES[n.type],
            "fair_title": f.title,
            "period": _period(f),
            "venue": f.venue.name,
            "detail": detail,
            "prereg_url": f.prereg_url if n.type == "prereg_deadline" else None,
            "fair_url": f"{base_url}/fairs/{f.id}",
            "settings_url": f"{base_url}/mypage/settings",
            "unsubscribe_url": f"{base_url}/unsubscribe?token={setting.unsubscribe_token}",
        },
    )


def send_pending(db: Session, *, now: datetime, base_url: str) -> dict[str, int]:
    counts = {"sent": 0, "failed": 0, "skipped": 0, "retry": 0}
    while True:
        batch = db.scalars(
            select(Notification)
            .where(Notification.status == "pending", Notification.scheduled_at <= now, Notification.channel == "email")
            .options(selectinload(Notification.user), selectinload(Notification.fair).selectinload(Fair.venue))
            .order_by(Notification.id)
            .limit(BATCH)
        ).all()
        if not batch:
            break
        progressed = False
        for n in batch:
            setting = db.get(NotificationSetting, n.user_id)
            enabled = setting is not None and setting.email_enabled and getattr(setting, n.type)
            if not enabled or n.fair.status != "published" or not n.user.email:
                # 발송 전에 알림을 껐거나, 박람회가 숨겨졌거나, 이메일 없이 소셜 로그인으로 가입한 회원
                n.status = "skipped"
                counts["skipped"] += 1
                progressed = True
                continue
            try:
                mail.send(build_mail(n, setting, base_url))
                n.status, n.sent_at = "sent", now
                counts["sent"] += 1
                progressed = True
            except Exception:
                n.attempts += 1
                logger.exception("notification %s send failed (%s)", n.id, n.attempts)
                if n.attempts >= MAX_ATTEMPTS:
                    n.status = "failed"  # 관리자 대시보드에 띄운다
                    counts["failed"] += 1
                    progressed = True
                else:
                    counts["retry"] += 1
        db.commit()
        if not progressed:
            break  # 이번 실행에서 모두 실패: 다음 실행 때 다시 보낸다
    return counts


def log_changes(db: Session, fair: Fair, before: dict, changed_by: int | None) -> None:
    """관리자가 바꾼 필드를 fair_change_logs 에 남긴다."""
    for field, old in before.items():
        new = getattr(fair, field)
        if old != new:
            db.add(
                FairChangeLog(
                    fair_id=fair.id,
                    field_name=field,
                    old_value=None if old is None else str(old),
                    new_value=None if new is None else str(new),
                    changed_by=changed_by,
                )
            )


def unsubscribe(db: Session, token: str) -> bool:
    s = db.scalar(select(NotificationSetting).where(NotificationSetting.unsubscribe_token == token))
    if s is None:
        return False
    s.email_enabled = False
    db.commit()
    return True
