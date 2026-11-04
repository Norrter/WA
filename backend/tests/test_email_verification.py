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
