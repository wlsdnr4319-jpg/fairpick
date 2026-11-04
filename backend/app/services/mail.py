"""
메일 발송 (레퍼런스 9장 메일 구성·발송 수단).

- HTML 은 Jinja2 템플릿으로 만들고, 텍스트 버전도 함께 보낸다.
- 개발: SMTP_HOST 를 비워 두면 보내지 않고 로그로 남긴다. Mailpit 을 띄우면 실제 발송 없이 화면으로 확인할 수 있다
  (docker compose --profile mail up -d mailpit, SMTP_HOST=localhost, SMTP_PORT=1025, SMTP_STARTTLS=false).
- 운영: SMTP 계정이나 메일 발송 서비스(SES, Resend 등)의 SMTP 를 쓴다.
"""

import logging
import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_env = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parent.parent / "templates" / "email"),
    autoescape=select_autoescape(["html"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


@dataclass
class Mail:
    to: str
    subject: str
    template: str  # templates/email/<template>.html, .txt
    context: dict = field(default_factory=dict)


# 테스트에서 보낸 메일을 확인하려고 쓴다
outbox: list[EmailMessage] = []


def render(mail: Mail) -> EmailMessage:
    settings = get_settings()
    ctx = {"base_url": settings.app_base_url.rstrip("/"), **mail.context}
    msg = EmailMessage()
    msg["Subject"] = mail.subject
    msg["From"] = settings.mail_from
    msg["To"] = mail.to
    msg["Message-ID"] = make_msgid(domain="fairpick")
    if "unsubscribe_url" in ctx:
        # 메일 앱의 '수신 거부' 버튼
        msg["List-Unsubscribe"] = f"<{ctx['unsubscribe_url']}>"
    msg.set_content(_env.get_template(f"{mail.template}.txt").render(**ctx))
    msg.add_alternative(_env.get_template(f"{mail.template}.html").render(**ctx), subtype="html")
    return msg


def send(mail: Mail) -> None:
    """실패하면 예외를 던진다. 호출한 쪽에서 재시도 횟수를 센다."""
    settings = get_settings()
    msg = render(mail)
    outbox.append(msg)
    if not settings.smtp_host:
        logger.info("mail (not sent, SMTP_HOST empty) to=%s subject=%s", mail.to, mail.subject)
        return
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)
