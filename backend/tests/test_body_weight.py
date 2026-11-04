"""Подтягивания, брусья и гравитрон: нагрузка с учётом веса тела."""

from tests.helpers import (
    create_day,
    create_exercise,
    create_program,
    create_program_exercise,
    create_set,
    create_workout,
)


async def plan_with(client, headers, load_type, name):
    exercise = await create_exercise(client, headers, name, load_type=load_type)
    program = await create_program(client, headers, f"Программа {name}")
    day = await create_day(client, headers, program["id"])
    item = await create_program_exercise(client, headers, program["id"], day["id"], exercise["id"])
    workout = await create_workout(client, headers, program["id"], day["id"], "2026-10-05")
    return exercise, item, workout


async def set_body_weight(client, headers, value):
    response = await client.patch("/users/me", json={"body_weight": value}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def test_assisted_load_is_body_minus_counterweight(client, alice):
    exercise, item, workout = await plan_with(client, alice, "assisted", "Гравитрон")

    # Без веса тела гравитрон не посчитать
    response = await client.post(
        f"/scheduled-workouts/{workout['id']}/sets",
        json={"program_exercise_id": item["id"], "set_number": 1, "weight": 20, "reps": 8},
        headers=alice,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Set your body weight in the profile first"

    me = await set_body_weight(client, alice, 80)
    assert me["body_weight"] == 80

    first = await create_set(client, alice, workout["id"], item["id"], 1, 30, 8)
    assert first["load"] == 50
    assert first["body_weight"] == 80
    second = await create_set(client, alice, workout["id"], item["id"], 2, 20, 8)
    assert second["load"] == 60

    # Рекорд — меньший противовес, то есть большая нагрузка
    records = (await client.get(f"/exercises/{exercise['id']}/records", headers=alice)).json()
    assert records["max_weight"]["weight"] == 60
    assert records["total_volume"] == (50 + 60) * 8

    history = (await client.get(f"/exercises/{exercise['id']}/history", headers=alice)).json()
    assert [(row["weight"], row["entered_weight"]) for row in history] == [(50, 30), (60, 20)]

    # Вес тела изменился — старые подходы считаются по весу на тот момент
    await set_body_weight(client, alice, 75)
    third = await create_set(client, alice, workout["id"], item["id"], 3, 20, 8)
    assert third["load"] == 55
    history = (await client.get(f"/exercises/{exercise['id']}/history", headers=alice)).json()
    assert sorted(row["weight"] for row in history) == [50, 55, 60]

    # Противовес больше веса тела — нагрузка не уходит в минус
    fourth = await create_set(client, alice, workout["id"], item["id"], 4, 100, 8)
    assert fourth["load"] == 0


async def test_bodyweight_load_is_body_plus_extra(client, alice):
    exercise, item, workout = await plan_with(client, alice, "bodyweight", "Подтягивания")

    # Вес тела ещё не указан — подход записывается, нагрузка = доп. вес
    early = await create_set(client, alice, workout["id"], item["id"], 1, 10, 5)
    assert early["load"] == 10
    assert early["body_weight"] is None

    # Человек указал вес — подходы без веса тела пересчитываются
    await set_body_weight(client, alice, 70)
    history = (await client.get(f"/exercises/{exercise['id']}/history", headers=alice)).json()
    assert history[0]["weight"] == 80

    plain = await create_set(client, alice, workout["id"], item["id"], 2, 0, 10)
    assert plain["load"] == 70

    # Правка веса подхода пересчитывает нагрузку
    response = await client.patch(
        f"/scheduled-workouts/{workout['id']}/sets/{plain['id']}",
        json={"weight": 5},
        headers=alice,
    )
    assert response.json()["load"] == 75


async def test_changing_load_type_recalculates(client, alice):
    await set_body_weight(client, alice, 90)
    exercise, item, workout = await plan_with(client, alice, "external", "Своё")
    workout_set = await create_set(client, alice, workout["id"], item["id"], 1, 20, 10)
    assert workout_set["load"] == 20

    response = await client.patch(
        f"/exercises/{exercise['id']}",
        json={"load_type": "assisted"},
        headers=alice,
    )
    assert response.status_code == 200
    assert response.json()["load_type"] == "assisted"

    # Подход был записан как обычный, без веса тела — нагрузка 0, пока
    # вес тела не подставится
    await set_body_weight(client, alice, 90)
    history = (await client.get(f"/exercises/{exercise['id']}/history", headers=alice)).json()
    assert history[0]["weight"] == 70

    response = await client.patch(
        f"/exercises/{exercise['id']}",
        json={"load_type": "nonsense"},
        headers=alice,
    )
    assert response.status_code == 422


async def test_body_weight_validation(client, alice):
    for value in (5, 500):
        response = await client.patch("/users/me", json={"body_weight": value}, headers=alice)
        assert response.status_code == 422

    me = await set_body_weight(client, alice, 82.5)
    assert me["body_weight"] == 82.5
    me = await set_body_weight(client, alice, None)
    assert me["body_weight"] is None
