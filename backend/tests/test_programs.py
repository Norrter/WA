from tests.helpers import (
    create_day,
    create_exercise,
    create_program,
    create_program_exercise,
)


async def test_program_crud(client, alice):
    program = await create_program(client, alice, name="Фулбоди")
    program_id = program["id"]
    assert program == {
        "id": program_id,
        "name": "Фулбоди",
        "description": "Описание",
    }

    response = await client.get("/programs", headers=alice)
    assert response.json() == [program]

    response = await client.put(
        f"/programs/{program_id}",
        json={"name": "Фулбоди 2"},
        headers=alice,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Фулбоди 2"
    assert response.json()["description"] is None

    response = await client.patch(
        f"/programs/{program_id}",
        json={"description": "Три раза в неделю"},
        headers=alice,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Фулбоди 2"
    assert response.json()["description"] == "Три раза в неделю"

    response = await client.delete(f"/programs/{program_id}", headers=alice)
    assert response.status_code == 204

    response = await client.get(f"/programs/{program_id}", headers=alice)
    assert response.status_code == 404
    assert (await client.get("/programs", headers=alice)).json() == []


async def test_program_detail_contains_days_and_exercises_in_order(client, alice):
    exercise = await create_exercise(client, alice)
    program = await create_program(client, alice)
    day_b = await create_day(client, alice, program["id"], "День B", 2)
    day_a = await create_day(client, alice, program["id"], "День A", 1)
    await create_program_exercise(
        client, alice, program["id"], day_a["id"], exercise["id"], order_index=2
    )
    await create_program_exercise(
        client, alice, program["id"], day_a["id"], exercise["id"], order_index=1
    )

    response = await client.get(f"/programs/{program['id']}", headers=alice)
    assert response.status_code == 200
    body = response.json()

    assert [day["id"] for day in body["days"]] == [day_a["id"], day_b["id"]]
    exercises = body["days"][0]["exercises"]
    assert [item["order_index"] for item in exercises] == [1, 2]
    assert exercises[0]["exercise"] == {
        "id": exercise["id"],
        "name": exercise["name"],
    }


async def test_program_validation(client, alice):
    for payload in ({"name": ""}, {"name": " "}, {"name": "x" * 151}, {}):
        response = await client.post("/programs", json=payload, headers=alice)
        assert response.status_code == 422, payload

    program = await create_program(client, alice)

    response = await client.patch(
        f"/programs/{program['id']}", json={"name": None}, headers=alice
    )
    assert response.status_code == 422


async def test_programs_pagination(client, alice):
    for index in range(3):
        await create_program(client, alice, name=f"P{index}")

    response = await client.get(
        "/programs", params={"limit": 2, "offset": 1}, headers=alice
    )
    assert [item["name"] for item in response.json()] == ["P1", "P2"]


async def test_program_is_private(client, alice, bob):
    program = await create_program(client, alice)
    url = f"/programs/{program['id']}"

    assert (await client.get("/programs", headers=bob)).json() == []
    assert (await client.get(url, headers=bob)).status_code == 404
    assert (
        await client.put(url, json={"name": "Чужая"}, headers=bob)
    ).status_code == 404
    assert (
        await client.patch(url, json={"name": "Чужая"}, headers=bob)
    ).status_code == 404
    assert (await client.delete(url, headers=bob)).status_code == 404

    response = await client.get(url, headers=alice)
    assert response.status_code == 200
    assert response.json()["name"] == program["name"]


async def test_programs_require_auth(client):
    assert (await client.get("/programs")).status_code in (401, 403)
    assert (
        await client.post("/programs", json={"name": "X"})
    ).status_code in (401, 403)
