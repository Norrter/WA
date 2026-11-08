"""Отправка писем.

Два способа, выбирается по настройкам в .env:
- RESEND_API_KEY задан — через Resend по HTTPS. Работает везде, в том
  числе на бесплатном Render, где почтовые порты 25/465/587 закрыты;
- иначе SMTP_* — через SMTP-сервер (например, Яндекс Почту).

Если не задано ни то ни другое, письмо не уходит, а печатается в консоль
сервера: так можно разрабатывать без почты. Ошибки отправки только
записываются в лог — из-за упавшей почты регистрация, заявка или
комментарий не должны ломаться.
"""

import asyncio
import json
import logging
import smtplib
import ssl
import urllib.error
import urllib.request
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from app.config import settings


logger = logging.getLogger("app.mailer")

RESEND_URL = "https://api.resend.com/emails"


def mail_provider() -> str:
    """resend, smtp или console (почта выключена)."""
    if settings.resend_api_key:
        return "resend"
    if settings.smtp_host:
        return "smtp"
    return "console"


def mail_enabled() -> bool:
    return mail_provider() != "console"


def sender_address() -> str:
    if mail_provider() == "resend":
        return settings.mail_from or settings.smtp_from or settings.smtp_user
    return settings.smtp_from or settings.smtp_user


# ----- SMTP -----

def build_message(to: str, subject: str, text: str, html: str | None = None) -> EmailMessage:
    sender = sender_address()

    message = EmailMessage()
    message["From"] = formataddr((settings.smtp_from_name, sender))
    message["To"] = to
    message["Subject"] = subject
    message["Message-ID"] = make_msgid(domain=sender.split("@")[-1] if "@" in sender else None)
    message.set_content(text)

    if html:
        message.add_alternative(html, subtype="html")

    return message


def _send_smtp(message: EmailMessage) -> None:
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


# ----- Resend (HTTPS) -----

def resend_payload(to: str, subject: str, text: str, html: str | None = None) -> dict:
    payload = {
        "from": formataddr((settings.smtp_from_name, sender_address())),
        "to": [to],
        "subject": subject,
        "text": text,
    }
    if html:
        payload["html"] = html
    return payload


def _send_resend(payload: dict) -> None:
    request = urllib.request.Request(
        RESEND_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "greeks-gym-backend",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            response.read()
    except urllib.error.HTTPError as error:
        # Resend объясняет причину в теле ответа: домен не подтверждён и т. п.
        detail = error.read().decode("utf-8", "replace")
        raise RuntimeError(f"Resend ответил {error.code}: {detail}") from error


# ----- Общая точка входа -----

async def send_email(to: str, subject: str, text: str, html: str | None = None) -> bool:
    """Отправить письмо. Возвращает True, если его принял почтовый сервис."""
    provider = mail_provider()

    if provider == "console":
        print(f"\n[почта выключена: нет RESEND_API_KEY и SMTP_HOST]\nКому: {to}\nТема: {subject}\n\n{text}\n", flush=True)
        return False

    try:
        if provider == "resend":
            await asyncio.to_thread(_send_resend, resend_payload(to, subject, text, html))
        else:
            await asyncio.to_thread(_send_smtp, build_message(to, subject, text, html))
    except Exception:
        logger.exception("Не удалось отправить письмо на %s (%s)", to, provider)
        return False

    return True
