"""Подтверждение почты: письмо при регистрации, ссылка, повторная отправка."""

import pytest

from app.api import auth as auth_api
from app.core.security import create_email_token
from tests.helpers import register, register_and_login


@pytest.fixture
def sent(monkeypatch):
    """Перехватываем письма вместо отправки."""
    letters = []

    async def fake_send(to, subject, text, html=None):
        letters.append({"to": to, "subject": subject, "text": text})
        return True

    monkeypatch.setattr("app.services.emails.send_email", fake_send)
    auth_api._last_resend.clear()
    return letters


async def test_registration_sends_link_and_user_is_not_verified(client, sent):
    response = await register(client, "alice")
    assert response.status_code == 201
    assert response.json()["email_verified"] is False

    assert len(sent) == 1
    assert sent[0]["to"] == "alice@example.com"
    assert "#/verify-email/" in sent[0]["text"]


async def test_link_verifies_email(client, sent):
    headers = await register_and_login(client, "alice")
    me = (await client.get("/auth/me", headers=headers)).json()

    token = sent[0]["text"].split("#/verify-email/")[1].split()[0]
    response = await client.post("/auth/verify-email", json={"token": token})
    assert response.status_code == 200
    assert response.json() == {"email": "alice@example.com", "email_verified": True}

    me = (await client.get("/auth/me", headers=headers)).json()
    assert me["email_verified"] is True

    # повторный переход по той же ссылке не ломается
    response = await client.post("/auth/verify-email", json={"token": token})
    assert response.status_code == 200


async def test_bad_token_is_rejected(client, sent):
    response = await client.post("/auth/verify-email", json={"token": "nonsense"})
    assert response.status_code == 400


async def test_old_link_does_not_fit_new_email(client, sent):
    headers = await register_and_login(client, "alice")
    me = (await client.get("/auth/me", headers=headers)).json()
    old_token = create_email_token(me["id"], "alice@example.com")

    response = await client.patch("/users/me", headers=headers, json={"email": "new@example.com"})
    assert response.status_code == 200
    assert response.json()["email_verified"] is False
    assert sent[-1]["to"] == "new@example.com"

    response = await client.post("/auth/verify-email", json={"token": old_token})
    assert response.status_code == 400


async def test_resend_is_limited(client, sent):
    headers = await register_and_login(client, "alice")

    response = await client.post("/auth/verify-email/resend", headers=headers)
    assert response.status_code == 204
    assert len(sent) == 2

    response = await client.post("/auth/verify-email/resend", headers=headers)
    assert response.status_code == 429


async def test_new_lead_notifies_coach(client, sent, monkeypatch):
    monkeypatch.setattr("app.config.settings.lead_notify_emails", ["coach@example.com"])

    response = await client.post(
        "/public/leads",
        json={"name": "Иван", "contact": "@ivan", "goal": "сбросить 5 кг"},
    )
    assert response.status_code == 201

    assert sent[-1]["to"] == "coach@example.com"
    assert "@ivan" in sent[-1]["text"]



# ----- Дневник закрыт до подтверждения почты -----

@pytest.fixture
def lock_on(monkeypatch):
    from datetime import datetime, timezone
    monkeypatch.setattr(
        "app.config.settings.email_required_since",
        datetime(2000, 1, 1, tzinfo=timezone.utc),
    )


async def test_new_unverified_user_cannot_write_diary(client, sent, lock_on):
    headers = await register_and_login(client, "alice")
    me = (await client.get("/auth/me", headers=headers)).json()
    assert me["diary_locked"] is True

    # смотреть можно
    response = await client.get("/scheduled-workouts", headers=headers)
    assert response.status_code == 200

    # записывать — нет
    response = await client.post(
        "/scheduled-workouts", headers=headers, json={"scheduled_date": "2026-11-10"}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Confirm your email to use the diary"

    response = await client.post(
        "/nutrition/entries", headers=headers, json={"date": "2026-11-10", "name": "Овсянка"}
    )
    assert response.status_code == 403


async def test_diary_opens_after_verification(client, sent, lock_on):
    headers = await register_and_login(client, "alice")

    token = sent[0]["text"].split("#/verify-email/")[1].split()[0]
    assert (await client.post("/auth/verify-email", json={"token": token})).status_code == 200

    me = (await client.get("/auth/me", headers=headers)).json()
    assert me["diary_locked"] is False

    response = await client.post("/nutrition/entries", headers=headers, json={"date": "2026-11-10"})
    assert response.status_code != 403


async def test_old_accounts_are_not_locked(client, sent):
    # в conftest дата замка — в далёком будущем: все аккаунты «старые»
    headers = await register_and_login(client, "alice")
    me = (await client.get("/auth/me", headers=headers)).json()
    assert me["email_verified"] is False
    assert me["diary_locked"] is False


async def test_locked_user_cannot_create_program(client, sent, lock_on):
    headers = await register_and_login(client, "alice")

    response = await client.get("/programs", headers=headers)
    assert response.status_code == 200

    response = await client.post("/programs", headers=headers, json={"name": "Моя программа"})
    assert response.status_code == 403



# ----- Отправка через Resend -----

async def test_resend_is_used_when_key_is_set(monkeypatch):
    from app.core import mailer

    monkeypatch.setattr("app.config.settings.resend_api_key", "re_test")
    monkeypatch.setattr("app.config.settings.mail_from", "noreply@greeksgym.ru")

    calls = []
    monkeypatch.setattr(mailer, "_send_resend", lambda payload: calls.append(payload))

    assert mailer.mail_provider() == "resend"
    assert await mailer.send_email("user@example.com", "Тема", "Текст", "<p>Текст</p>") is True

    [payload] = calls
    assert payload["to"] == ["user@example.com"]
    assert payload["from"].endswith("<noreply@greeksgym.ru>")
    assert payload["subject"] == "Тема"
    assert payload["html"] == "<p>Текст</p>"


async def test_mail_failure_does_not_raise(monkeypatch):
    from app.core import mailer

    monkeypatch.setattr("app.config.settings.resend_api_key", "re_test")

    def boom(payload):
        raise RuntimeError("Resend ответил 403")

    monkeypatch.setattr(mailer, "_send_resend", boom)
    assert await mailer.send_email("user@example.com", "Тема", "Текст") is False
