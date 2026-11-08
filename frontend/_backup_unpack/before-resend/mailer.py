"""Отправка писем через SMTP.

Настройки — SMTP_* в .env. Пока SMTP_HOST пустой, письмо не уходит,
а печатается в консоль сервера: так можно разрабатывать без почты.
Ошибки отправки только записываются в лог — из-за упавшей почты
регистрация или заявка не должны ломаться.
"""

import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from app.config import settings


logger = logging.getLogger("app.mailer")


def mail_enabled() -> bool:
    return bool(settings.smtp_host)


def build_message(to: str, subject: str, text: str, html: str | None = None) -> EmailMessage:
    sender = settings.smtp_from or settings.smtp_user

    message = EmailMessage()
    message["From"] = formataddr((settings.smtp_from_name, sender))
    message["To"] = to
    message["Subject"] = subject
    message["Message-ID"] = make_msgid(domain=sender.split("@")[-1] if "@" in sender else None)
    message.set_content(text)

    if html:
        message.add_alternative(html, subtype="html")

    return message


def _send_sync(message: EmailMessage) -> None:
    context = ssl.create_default_context()

    if settings.smtp_port == 465:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=context, timeout=20) as server:
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            server.starttls(context=context)
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)


async def send_email(to: str, subject: str, text: str, html: str | None = None) -> bool:
    """Отправить письмо. Возвращает True, если оно ушло на SMTP-сервер."""
    if not mail_enabled():
        print(f"\n[почта выключена: SMTP_HOST не задан]\nКому: {to}\nТема: {subject}\n\n{text}\n", flush=True)
        return False

    try:
        await asyncio.to_thread(_send_sync, build_message(to, subject, text, html))
    except Exception:
        logger.exception("Не удалось отправить письмо на %s", to)
        return False

    return True
