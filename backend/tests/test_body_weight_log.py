"""Журнал веса тела."""

from datetime import date, timedelta

from tests.test_coach import coach, make_client  # noqa: F401 — фикстуры


def day(offset: int) -> str:
    return (date.today() + timedelta(days=offset)).isoformat()


async def add(client, headers, weight, when=None, expected=201):
    payload = {"weight": weight}
    if when:
        payload["date"] = when
    response = await client.post("/body-weight", json=payload, headers=headers)
    assert response.status_code == expected, response.text
    return response.json()


async def me(client, headers):
    return (await client.get("/auth/me", headers=headers)).json()


async def test_log_and_current_weight(client, alice, bob):
    await add(client, alice, 82, day(-14))
    await add(client, alice, 81.2, day(-7))
    today_entry = await add(client, alice, 80.5)
    assert today_entry["date"] == day(0)

    # Текущий вес в профиле — последняя запись
    assert (await me(client, alice))["body_weight"] == 80.5

    # Повторная запись за день заменяет прежнюю
    await add(client, alice, 80.1)
    entries = (await client.get("/body-weight", headers=alice)).json()
    assert [(e["date"], e["weight"]) for e in entries] == [
        (day(-14), 82),
        (day(-7), 81.2),
        (day(0), 80.1),
    ]

    # Запись задним числом не меняет текущий вес
    await add(client, alice, 90, day(-30))
    assert (await me(client, alice))["body_weight"] == 80.1

    # Период
    entries = (
        await client.get("/body-weight", params={"date_from": day(-10)}, headers=alice)
    ).json()
    assert len(entries) == 2

    # Удаление последней записи — текущим становится предыдущий вес
    response = await client.delete(f"/body-weight/{today_entry['id']}", headers=alice)
    assert response.status_code == 204
    assert (await me(client, alice))["body_weight"] == 81.2

    # Чужие записи не видны и не удаляются
    assert (await client.get("/body-weight", headers=bob)).json() == []
    response = await client.delete(f"/body-weight/{entries[0]['id']}", headers=bob)
    assert response.status_code == 404


async def test_validation_and_profile(client, alice):
    await add(client, alice, 10, expected=422)
    await add(client, alice, 80, day(1), expected=400)

    # Вес из профиля попадает в журнал за сегодня
    response = await client.patch("/users/me", json={"body_weight": 77}, headers=alice)
    assert response.status_code == 200
    entries = (await client.get("/body-weight", headers=alice)).json()
    assert [(e["date"], e["weight"]) for e in entries] == [(day(0), 77)]


async def test_coach_sees_client_weight(client, coach, alice, bob):
    alice_id = await make_client(client, coach, alice)
    await add(client, alice, 70, day(-3))

    response = await client.get(f"/coach/clients/{alice_id}/body-weight", headers=coach)
    assert response.status_code == 200
    assert [e["weight"] for e in response.json()] == [70]

    bob_id = (await me(client, bob))["id"]
    response = await client.get(f"/coach/clients/{bob_id}/body-weight", headers=coach)
    assert response.status_code == 404
