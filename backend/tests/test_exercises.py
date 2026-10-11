from tests.helpers import (
    create_day,
    create_exercise,
    create_program,
    create_program_exercise,
)


async def test_exercise_crud(client, alice):
    # create
    exercise = await create_exercise(
        client,
        alice,
        name="  Жим лёжа  ",
        muscle_group="Грудь",
        equipment="Штанга",
    )
    assert exercise["name"] == "Жим лёжа"  # пробелы по краям обрезаны
    assert exercise["created_by_user_id"] is not None
    exercise_id = exercise["id"]

    # read one + list
    response = await client.get(f"/exercises/{exercise_id}", headers=alice)
    assert response.status_code == 200
    assert response.json() == exercise

    response = await client.get("/exercises", headers=alice)
    assert [item["id"] for item in response.json()] == [exercise_id]

    # update (PUT заменяет все поля)
    response = await client.put(
        f"/exercises/{exercise_id}",
        json={"name": "Жим на наклонной", "muscle_group": "Грудь"},
        headers=alice,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Жим на наклонной"
    assert response.json()["equipment"] is None

    # partial update (PATCH меняет только присланное)
    response = await client.patch(
        f"/exercises/{exercise_id}",
        json={"equipment": "Гантели"},
        headers=alice,
    )
    assert response.status_code == 200
    assert response.json()["equipment"] == "Гантели"
    assert response.json()["name"] == "Жим на наклонной"

    # delete
    response = await client.delete(f"/exercises/{exercise_id}", headers=alice)
    assert response.status_code == 204

    response = await client.get(f"/exercises/{exercise_id}", headers=alice)
    assert response.status_code == 404


async def test_exercises_require_auth(client):
    assert (await client.get("/exercises")).status_code in (401, 403)
    assert (
        await client.post("/exercises", json={"name": "X"})
    ).status_code in (401, 403)


async def test_exercise_validation(client, alice):
    for payload in (
        {"name": ""},
        {"name": "   "},
        {"name": "x" * 151},
        {},
    ):
        response = await client.post("/exercises", json=payload, headers=alice)
        assert response.status_code == 422, payload

    exercise = await create_exercise(client, alice)

    response = await client.patch(
        f"/exercises/{exercise['id']}", json={"name": None}, headers=alice
    )
    assert response.status_code == 422


async def test_shared_exercise_is_visible_but_read_only(
    client, alice, shared_exercise
):
    response = await client.get(f"/exercises/{shared_exercise}", headers=alice)
    assert response.status_code == 200
    assert response.json()["created_by_user_id"] is None

    response = await client.put(
        f"/exercises/{shared_exercise}", json={"name": "Взлом"}, headers=alice
    )
    assert response.status_code == 403

    response = await client.patch(
        f"/exercises/{shared_exercise}", json={"name": "Взлом"}, headers=alice
    )
    assert response.status_code == 403

    response = await client.delete(
        f"/exercises/{shared_exercise}", headers=alice
    )
    assert response.status_code == 403


async def test_private_exercise_is_hidden_from_other_users(client, alice, bob):
    exercise = await create_exercise(client, alice)
    url = f"/exercises/{exercise['id']}"

    assert (await client.get(url, headers=bob)).status_code == 404
    assert (
        await client.put(url, json={"name": "Чужое"}, headers=bob)
    ).status_code == 404
    assert (await client.delete(url, headers=bob)).status_code == 404
    assert (await client.get("/exercises", headers=bob)).json() == []

    # у владельца всё на месте и не изменилось
    response = await client.get(url, headers=alice)
    assert response.json()["name"] == exercise["name"]


async def test_exercise_filters_and_pagination(client, alice, shared_exercise):
    await create_exercise(
        client, alice, name="Жим лёжа", muscle_group="Грудь", equipment="Штанга"
    )
    await create_exercise(
        client, alice, name="Жим гантелей", muscle_group="Грудь", equipment="Гантели"
    )
    await create_exercise(
        client, alice, name="Тяга 100%", muscle_group="Спина", equipment="Штанга"
    )

    async def names(**params):
        response = await client.get("/exercises", params=params, headers=alice)
        assert response.status_code == 200
        return [item["name"] for item in response.json()]

    assert len(await names()) == 4  # три своих + одно общее
    assert await names(search="жим") == ["Жим лёжа", "Жим гантелей"]
    assert await names(muscle_group="грудь") == ["Жим лёжа", "Жим гантелей"]
    assert await names(equipment="Штанга", muscle_group="Спина") == ["Тяга 100%"]
    # % ищется как обычный символ, а не как «что угодно»
    assert await names(search="100%") == ["Тяга 100%"]
    assert await names(search="%") == ["Тяга 100%"]

    assert len(await names(limit=2)) == 2
    assert len(await names(limit=2, offset=3)) == 1

    response = await client.get("/exercises", params={"limit": 0}, headers=alice)
    assert response.status_code == 422


async def test_exercise_in_use_cannot_be_deleted(client, alice):
    exercise = await create_exercise(client, alice)
    program = await create_program(client, alice)
    day = await create_day(client, alice, program["id"])
    await create_program_exercise(
        client, alice, program["id"], day["id"], exercise["id"]
    )

    response = await client.delete(f"/exercises/{exercise['id']}", headers=alice)
    assert response.status_code == 409

    assert (
        await client.get(f"/exercises/{exercise['id']}", headers=alice)
    ).status_code == 200
