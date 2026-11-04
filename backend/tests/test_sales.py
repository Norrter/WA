"""Главная страница: тарифы и заявки."""

import pytest

from app.api import sales
from tests.test_admin import admin  # noqa: F401 — фикстура
from tests.test_coach import coach  # noqa: F401 — фикстура


@pytest.fixture(autouse=True)
def reset_rate_limit():
    sales._recent.clear()
    yield
    sales._recent.clear()


async def make_offer(client, admin_headers, **values):
    payload = {"title": "Онлайн-ведение", "kind": "online", "price": 5000, **values}
    response = await client.post("/admin/tables/offers/rows", json=payload, headers=admin_headers)
    assert response.status_code == 201, response.text
    return response.json()


async def test_public_offers(client, admin):
    await make_offer(client, admin, title="Б", order_index=2, features="Раз\n\n  Два  \n")
    await make_offer(client, admin, title="А", order_index=1, is_featured=True)
    await make_offer(client, admin, title="Скрытый", is_active=False)

    # Без входа
    response = await client.get("/public/offers")
    assert response.status_code == 200
    offers = response.json()
    assert [o["title"] for o in offers] == ["А", "Б"]
    assert offers[1]["features"] == ["Раз", "Два"]
    assert offers[0]["is_featured"] is True
    assert offers[0]["features"] == []


async def test_lead_flow(client, admin, coach, alice):
    offer = await make_offer(client, admin, title="Онлайн-ведение")
    hidden = await make_offer(client, admin, title="Старый", is_active=False)

    response = await client.post(
        "/public/leads",
        json={"offer_id": offer["id"], "name": " Иван ", "contact": "@ivan", "goal": "Похудеть"},
    )
    assert response.status_code == 201, response.text

    # Без тарифа — просто вопрос
    response = await client.post("/public/leads", json={"name": "Оля", "contact": "+7 900 000-00-00"})
    assert response.status_code == 201

    # Скрытый или несуществующий тариф
    for offer_id in (hidden["id"], 99999):
        response = await client.post(
            "/public/leads", json={"offer_id": offer_id, "name": "X", "contact": "@xxx"}
        )
        assert response.status_code == 404

    # Проверки полей
    response = await client.post("/public/leads", json={"name": "", "contact": "@x"})
    assert response.status_code == 422

    # Бот заполнил скрытое поле — заявка не сохраняется
    response = await client.post(
        "/public/leads", json={"name": "Bot", "contact": "spam@x.ru", "website": "http://spam"}
    )
    assert response.status_code == 201

    # Тренер видит заявки, новые сверху
    leads = (await client.get("/leads", headers=coach)).json()
    assert [(l["name"], l["offer_title"], l["status"]) for l in leads] == [
        ("Оля", None, "new"),
        ("Иван", "Онлайн-ведение", "new"),
    ]

    # Админ тоже, обычный пользователь — нет, без входа — нет
    assert (await client.get("/leads", headers=admin)).status_code == 200
    assert (await client.get("/leads", headers=alice)).status_code == 403
    assert (await client.get("/leads")).status_code in (401, 403)

    ivan = leads[1]
    response = await client.patch(
        f"/leads/{ivan['id']}", json={"status": "in_progress", "note": "Написал в TG"}, headers=coach
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"
    assert response.json()["note"] == "Написал в TG"

    assert [l["name"] for l in (await client.get("/leads", params={"status": "new"}, headers=coach)).json()] == ["Оля"]

    response = await client.patch(f"/leads/{ivan['id']}", json={"status": "bad"}, headers=coach)
    assert response.status_code == 422
    assert (await client.patch(f"/leads/{ivan['id']}", json={"status": "done"}, headers=alice)).status_code == 403

    # Удаление тарифа не удаляет заявку — название сохраняется
    response = await client.delete(f"/admin/tables/offers/rows/{offer['id']}", headers=admin)
    assert response.status_code == 204
    lead = next(l for l in (await client.get("/leads", headers=coach)).json() if l["id"] == ivan["id"])
    assert lead["offer_id"] is None and lead["offer_title"] == "Онлайн-ведение"

    assert (await client.delete(f"/leads/{ivan['id']}", headers=coach)).status_code == 204
    assert (await client.delete(f"/leads/{ivan['id']}", headers=coach)).status_code == 404


async def test_lead_rate_limit(client):
    for _ in range(sales.LEADS_PER_WINDOW):
        response = await client.post("/public/leads", json={"name": "Иван", "contact": "@ivan"})
        assert response.status_code == 201

    response = await client.post("/public/leads", json={"name": "Иван", "contact": "@ivan"})
    assert response.status_code == 429

    # С другого адреса — можно
    response = await client.post(
        "/public/leads",
        json={"name": "Оля", "contact": "@olya"},
        headers={"X-Forwarded-For": "10.0.0.7"},
    )
    assert response.status_code == 201
