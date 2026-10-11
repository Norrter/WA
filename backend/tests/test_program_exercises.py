import pytest_asyncio

from tests.helpers import (
    create_day,
    create_exercise,
    create_program,
    create_program_exercise,
)


@pytest_asyncio.fixture
async def setup(client, alice):
    exercise = await create_exercise(client, alice)
    program = await create_program(client, alice)
    day = await create_day(client, alice, program["id"])

    return {
        "exercise": exercise,
        "program": program,
        "day": day,
        "base": f"/programs/{program['id']}/days/{day['id']}/exercises",
    }


async def test_program_exercise_crud(client, alice, setup):
    base = setup["base"]
    exercise = setup["exercise"]

    item = await create_program_exercise(
        client,
        alice,
        setup["program"]["id"],
        setup["day"]["id"],
        exercise["id"],
        notes="Пауза внизу",
    )
    assert item["sets"] == 3
    assert item["target_reps"] == 8
    assert item["target_weight"] == 60
    assert item["notes"] == "Пауза внизу"
    assert item["exercise"] == {"id": exercise["id"], "name": exercise["name"]}

    response = await client.get(base, headers=alice)
    assert response.json() == [item]

    response = await client.get(f"{base}/{item['id']}", headers=alice)
    assert response.status_code == 200
    assert response.json() == item

    other_exercise = await create_exercise(client, alice, name="Присед")

    response = await client.put(
        f"{base}/{item['id']}",
        json={"exercise_id": other_exercise["id"], "order_index": 2, "sets": 5},
        headers=alice,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["exercise"]["name"] == "Присед"
    assert body["sets"] == 5
    assert body["target_reps"] is None  # PUT заменяет всё
    assert body["notes"] is None

    response = await client.patch(
        f"{base}/{item['id']}",
        json={"target_weight": 82.5},
        headers=alice,
    )
    assert response.status_code == 200
    assert response.json()["target_weight"] == 82.5
    assert response.json()["sets"] == 5
    assert response.json()["exercise"]["name"] == "Присед"

    response = await client.delete(f"{base}/{item['id']}", headers=alice)
    assert response.status_code == 204
    assert (
        await client.get(f"{base}/{item['id']}", headers=alice)
    ).status_code == 404


async def test_program_exercise_validation(client, alice, setup):
    valid = {"exercise_id": setup["exercise"]["id"], "order_index": 1, "sets": 3}

    for changes in (
        {"sets": 0},
        {"sets": -1},
        {"target_reps": 0},
        {"target_weight": -5},
        {"rest_seconds": -1},
        {"order_index": -1},
    ):
        response = await client.post(
            setup["base"], json={**valid, **changes}, headers=alice
        )
        assert response.status_code == 422, changes

    response = await client.post(
        setup["base"], json={**valid, "exercise_id": 9999}, headers=alice
    )
    assert response.status_code == 404


async def test_can_use_shared_but_not_foreign_exercise(
    client, alice, bob, setup, shared_exercise
):
    program_id, day_id = setup["program"]["id"], setup["day"]["id"]

    await create_program_exercise(
        client, alice, program_id, day_id, shared_exercise, order_index=1
    )

    bobs_exercise = await create_exercise(client, bob, name="Секретное")

    response = await client.post(
        setup["base"],
        json={"exercise_id": bobs_exercise["id"], "order_index": 2, "sets": 3},
        headers=alice,
    )
    assert response.status_code == 404


async def test_duplicate_order_and_reorder(client, alice, setup):
    program_id, day_id = setup["program"]["id"], setup["day"]["id"]
    exercise_id = setup["exercise"]["id"]
    base = setup["base"]

    first = await create_program_exercise(
        client, alice, program_id, day_id, exercise_id, order_index=1
    )
    second = await create_program_exercise(
        client, alice, program_id, day_id, exercise_id, order_index=2
    )

    response = await client.post(
        base,
        json={"exercise_id": exercise_id, "order_index": 2, "sets": 3},
        headers=alice,
    )
    assert response.status_code == 409

    response = await client.post(
        f"{base}/reorder",
        json={"ids": [second["id"], first["id"]]},
        headers=alice,
    )
    assert response.status_code == 200
    assert [(i["id"], i["order_index"]) for i in response.json()] == [
        (second["id"], 1),
        (first["id"], 2),
    ]

    response = await client.post(
        f"{base}/reorder", json={"ids": [first["id"]]}, headers=alice
    )
    assert response.status_code == 400


async def test_program_exercises_are_private(client, alice, bob, setup):
    item = await create_program_exercise(
        client,
        alice,
        setup["program"]["id"],
        setup["day"]["id"],
        setup["exercise"]["id"],
    )
    base = setup["base"]
    url = f"{base}/{item['id']}"
    payload = {"exercise_id": setup["exercise"]["id"], "order_index": 9, "sets": 1}

    assert (await client.get(base, headers=bob)).status_code == 404
    assert (await client.post(base, json=payload, headers=bob)).status_code == 404
    assert (await client.get(url, headers=bob)).status_code == 404
    assert (await client.put(url, json=payload, headers=bob)).status_code == 404
    assert (
        await client.patch(url, json={"sets": 1}, headers=bob)
    ).status_code == 404
    assert (await client.delete(url, headers=bob)).status_code == 404

    response = await client.get(url, headers=alice)
    assert response.json() == item


async def test_program_exercise_must_belong_to_day_in_url(client, alice, setup):
    item = await create_program_exercise(
        client,
        alice,
        setup["program"]["id"],
        setup["day"]["id"],
        setup["exercise"]["id"],
    )
    other_day = await create_day(
        client, alice, setup["program"]["id"], "Другой день", 2
    )

    response = await client.get(
        f"/programs/{setup['program']['id']}/days/{other_day['id']}"
        f"/exercises/{item['id']}",
        headers=alice,
    )
    assert response.status_code == 404
