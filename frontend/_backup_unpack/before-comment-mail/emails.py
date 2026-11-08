"""Тексты писем: подтверждение почты и новая заявка."""

from html import escape

from app.config import settings
from app.core.mailer import send_email
from app.core.security import create_email_token


def _layout(title: str, body_html: str) -> str:
    # Простая вёрстка: почтовые программы плохо понимают современный CSS
    return f"""<!doctype html>
<html lang="ru">
<body style="margin:0;padding:24px;background:#f3efea;font-family:Arial,Helvetica,sans-serif;color:#1a1714">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
    <tr><td align="center">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
             style="max-width:520px;background:#ffffff;border-radius:16px;padding:28px">
        <tr><td>
          <p style="margin:0 0 18px;font-size:18px;font-weight:bold;color:#a8420f">Greek's Gym</p>
          <h1 style="margin:0 0 14px;font-size:22px;line-height:1.3">{title}</h1>
          {body_html}
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def verify_link(user_id: int, email: str) -> str:
    token = create_email_token(user_id, email)
    return f"{settings.frontend_url.rstrip('/')}/#/verify-email/{token}"


async def send_verification(user_id: int, username: str, email: str) -> bool:
    link = verify_link(user_id, email)
    hours = settings.email_verify_hours

    text = (
        f"Здравствуйте, {username}!\n\n"
        f"Чтобы подтвердить почту в Greek's Gym, откройте ссылку:\n{link}\n\n"
        f"Ссылка действует {hours} ч. Если вы не регистрировались — просто удалите это письмо."
    )
    html = _layout(
        "Подтвердите почту",
        f"""<p style="margin:0 0 20px;font-size:15px;line-height:1.55">
            Здравствуйте, {escape(username)}! Нажмите кнопку, чтобы подтвердить адрес
            <b>{escape(email)}</b>.</p>
          <p style="margin:0 0 22px">
            <a href="{escape(link)}" style="display:inline-block;padding:14px 22px;border-radius:12px;
               background:#f47a36;color:#1a0d05;font-weight:bold;font-size:15px;text-decoration:none">
               Подтвердить почту</a></p>
          <p style="margin:0;font-size:13px;line-height:1.5;color:#5c554d">
            Ссылка действует {hours} ч. Если вы не регистрировались в Greek's Gym,
            просто удалите это письмо.</p>""",
    )

    return await send_email(email, "Подтвердите почту — Greek's Gym", text, html)


def lead_recipients() -> list[str]:
    return settings.lead_notify_emails or settings.coach_emails


async def send_lead_notice(name: str, contact: str, offer_title: str | None, goal: str | None) -> None:
    recipients = lead_recipients()
    if not recipients:
        return

    offer = offer_title or "Пока не знает — нужна консультация"
    link = f"{settings.frontend_url.rstrip('/')}/#/coach/leads"

    text = (
        f"Новая заявка с сайта\n\n"
        f"Имя: {name}\nКонтакт: {contact}\nФормат: {offer}\n"
        + (f"Цель и опыт: {goal}\n" if goal else "")
        + f"\nВсе заявки: {link}"
    )
    rows = [("Имя", name), ("Контакт", contact), ("Формат", offer)]
    if goal:
        rows.append(("Цель и опыт", goal))
    table = "".join(
        f'<tr><td style="padding:6px 12px 6px 0;color:#5c554d;font-size:14px;vertical-align:top">{escape(k)}</td>'
        f'<td style="padding:6px 0;font-size:15px;font-weight:bold">{escape(v)}</td></tr>'
        for k, v in rows
    )
    html = _layout(
        "Новая заявка с сайта",
        f"""<table role="presentation" cellspacing="0" cellpadding="0" style="margin:0 0 20px">{table}</table>
          <p style="margin:0"><a href="{escape(link)}" style="color:#a8420f;font-weight:bold">Открыть заявки</a></p>""",
    )

    for to in recipients:
        await send_email(to, f"Новая заявка: {name}", text, html)
