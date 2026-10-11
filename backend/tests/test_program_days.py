from tests.helpers import create_day, create_program


async def test_program_day_crud(client, alice):
    program = await create_program(client, alice)
    base = f"/programs/{program['id']}/days"

    day = await create_day(client, alice, program["id"], "Ноги", 1)
    assert day["name"] == "Ноги"
    assert day["program_id"] == program["id"]
    assert day["exercises"] == []

    response = await client.get(base, headers=alice)
    assert [item["id"] for item in response.json()] == [day["id"]]

    response = await client.get(f"{base}/{day['id']}", headers=alice)
    assert response.status_code == 200
    assert response.json() == day

    response = await client.put(
        f"{base}/{day['id']}",
        json={"name": "Ноги и ягодицы", "order_index": 3},
        headers=alice,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Ноги и ягодицы"
    assert response.json()["order_index"] == 3

    response = await client.patch(
        f"{base}/{day['id']}", json={"name": "Низ"}, headers=alice
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Низ"
    assert response.json()["order_index"] == 3

    response = await client.delete(f"{base}/{day['id']}", headers=alice)
    assert response.status_code == 204
    assert (
        await client.get(f"{base}/{day['id']}", headers=alice)
    ).status_code == 404


async def test_program_day_validation(client, alice):
    program = await create_program(client, alice)
    base = f"/programs/{program['id']}/days"

    for payload in (
        {"name": "", "order_index": 1},
        {"name": "A", "order_index": -1},
        {"name": "A"},
        {"order_index": 1},
    ):
        response = await client.post(base, json=payload, headers=alice)
        assert response.status_code == 422, payload


async def test_duplicate_order_index_is_rejected(client, alice):
    program = await create_program(client, alice)
    other_program = await create_program(client, alice, name="Другая")
    base = f"/programs/{program['id']}/days"

    first = await create_day(client, alice, program["id"], "A", 1)
    second = await create_day(client, alice, program["id"], "B", 2)

    response = await client.post(
        base, json={"name": "C", "order_index": 1}, headers=alice
    )
    assert response.status_code == 409

    response = await client.patch(
        f"{base}/{second['id']}", json={"order_index": 1}, headers=alice
    )
    assert response.status_code == 409

    # в другой программе тот же номер свободен
    await create_day(client, alice, other_program["id"], "A", 1)

    # после отказа данные не испортились
    response = await client.get(base, headers=alice)
    assert [(d["id"], d["order_index"]) for d in response.json()] == [
        (first["id"], 1),
        (second["id"], 2),
    ]


async def test_reorder_days(client, alice):
    program = await create_program(client, alice)
    base = f"/programs/{program['id']}/days"
    a = await create_day(client, alice, program["id"], "A", 1)
    b = await create_day(client, alice, program["id"], "B", 2)
    c = await create_day(client, alice, program["id"], "C", 3)

    response = await client.post(
        f"{base}/reorder",
        json={"ids": [c["id"], a["id"], b["id"]]},
        headers=alice,
    )
    assert response.status_code == 200
    assert [(d["name"], d["order_index"]) for d in response.json()] == [
        ("C", 1),
        ("A", 2),
        ("B", 3),
    ]

    # список должен содержать все дни программы ровно по одному разу
    for ids in ([a["id"], b["id"]], [a["id"], b["id"], c["id"], 999]):
        response = await client.post(
            f"{base}/reorder", json={"ids": ids}, headers=alice
        )
        assert response.status_code == 400, ids

    response = await client.post(
        f"{base}/reorder", json={"ids": [a["id"], a["id"]]}, headers=alice
    )
    assert response.status_code == 422


async def test_program_days_are_private(client, alice, bob):
    program = await create_program(client, alice)
    day = await create_day(client, alice, program["id"])
    base = f"/programs/{program['id']}/days"
    payload = {"name": "Чужой", "order_index": 5}

    assert (await client.get(base, headers=bob)).status_code == 404
    assert (await client.post(base, json=payload, headers=bob)).status_code == 404
    assert (
        await client.get(f"{base}/{day['id']}", headers=bob)
    ).status_code == 404
    assert (
        await client.put(f"{base}/{day['id']}", json=payload, headers=bob)
    ).status_code == 404
    assert (
        await client.patch(f"{base}/{day['id']}", json={"name": "X"}, headers=bob)
    ).status_code == 404
    assert (
        await client.delete(f"{base}/{day['id']}", headers=bob)
    ).status_code == 404
    assert (
        await client.post(
            f"{base}/reorder", json={"ids": [day["id"]]}, headers=bob
        )
    ).status_code == 404

    # день нельзя достать через свою программу с чужим id дня
    bob_program = await create_program(client, bob)
    response = await client.get(
        f"/programs/{bob_program['id']}/days/{day['id']}", headers=bob
    )
    assert response.status_code == 404

    response = await client.get(f"{base}/{day['id']}", headers=alice)
    assert response.json()["name"] == day["name"]


async def test_deleting_program_deletes_its_days(client, alice):
    program = await create_program(client, alice)
    await create_day(client, alice, program["id"])

    await client.delete(f"/programs/{program['id']}", headers=alice)

    response = await client.get(
        f"/programs/{program['id']}/days", headers=alice
    )
    assert response.status_code == 404
