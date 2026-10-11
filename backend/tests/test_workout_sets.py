from tests.helpers import (
    build_workout,
    create_day,
    create_program_exercise,
    create_set,
)


async def test_workout_set_crud(client, alice):
    data = await build_workout(client, alice)
    workout_id = data["workout"]["id"]
    program_exercise_id = data["program_exercise"]["id"]
    base = f"/scheduled-workouts/{workout_id}/sets"

    workout_set = await create_set(
        client, alice, workout_id, program_exercise_id, 1, 60, 8
    )
    assert workout_set == {
        "id": workout_set["id"],
        "scheduled_workout_id": workout_id,
        "program_exercise_id": program_exercise_id,
        "set_number": 1,
        "weight": 60,
        "reps": 8,
        "completed": True,
    }
    url = f"{base}/{workout_set['id']}"

    response = await client.get(base, headers=alice)
    assert response.json() == [workout_set]

    response = await client.get(url, headers=alice)
    assert response.status_code == 200
    assert response.json() == workout_set

    response = await client.put(
        url,
        json={
            "program_exercise_id": program_exercise_id,
            "set_number": 2,
            "weight": 62.5,
            "reps": 6,
            "completed": False,
        },
        headers=alice,
    )
    assert response.status_code == 200
    assert response.json()["set_number"] == 2
    assert response.json()["weight"] == 62.5
    assert response.json()["completed"] is False

    response = await client.patch(url, json={"completed": True}, headers=alice)
    assert response.status_code == 200
    assert response.json()["completed"] is True
    assert response.json()["weight"] == 62.5
    assert response.json()["reps"] == 6

    response = await client.delete(url, headers=alice)
    assert response.status_code == 204
    assert (await client.get(url, headers=alice)).status_code == 404
    assert (await client.get(base, headers=alice)).json() == []


async def test_workout_set_validation(client, alice):
    data = await build_workout(client, alice)
    base = f"/scheduled-workouts/{data['workout']['id']}/sets"
    valid = {
        "program_exercise_id": data["program_exercise"]["id"],
        "set_number": 1,
        "weight": 60,
        "reps": 8,
    }

    for changes in (
        {"weight": -1},
        {"reps": 0},
        {"reps": -3},
        {"set_number": 0},
        {"weight": "тяжело"},
    ):
        response = await client.post(
            base, json={**valid, **changes}, headers=alice
        )
        assert response.status_code == 422, changes

    # вес 0 допустим: упражнения с собственным весом
    response = await client.post(base, json={**valid, "weight": 0}, headers=alice)
    assert response.status_code == 201

    workout_set = response.json()
    response = await client.patch(
        f"{base}/{workout_set['id']}", json={"reps": None}, headers=alice
    )
    assert response.status_code == 422


async def test_duplicate_set_number_is_rejected(client, alice):
    data = await build_workout(client, alice)
    workout_id = data["workout"]["id"]
    program_exercise_id = data["program_exercise"]["id"]
    base = f"/scheduled-workouts/{workout_id}/sets"

    await create_set(client, alice, workout_id, program_exercise_id, 1)
    second = await create_set(client, alice, workout_id, program_exercise_id, 2)

    response = await client.post(
        base,
        json={
            "program_exercise_id": program_exercise_id,
            "set_number": 1,
            "weight": 60,
            "reps": 8,
        },
        headers=alice,
    )
    assert response.status_code == 409

    response = await client.patch(
        f"{base}/{second['id']}", json={"set_number": 1}, headers=alice
    )
    assert response.status_code == 409

    response = await client.get(base, headers=alice)
    assert [s["set_number"] for s in response.json()] == [1, 2]


async def test_set_exercise_must_belong_to_workout_day(client, alice):
    data = await build_workout(client, alice)
    other_day = await create_day(
        client, alice, data["program"]["id"], "День B", 2
    )
    foreign = await create_program_exercise(
        client,
        alice,
        data["program"]["id"],
        other_day["id"],
        data["exercise"]["id"],
    )
    base = f"/scheduled-workouts/{data['workout']['id']}/sets"

    response = await client.post(
        base,
        json={
            "program_exercise_id": foreign["id"],
            "set_number": 1,
            "weight": 60,
            "reps": 8,
        },
        headers=alice,
    )
    assert response.status_code == 400

    workout_set = await create_set(
        client, alice, data["workout"]["id"], data["program_exercise"]["id"]
    )
    response = await client.patch(
        f"{base}/{workout_set['id']}",
        json={"program_exercise_id": foreign["id"]},
        headers=alice,
    )
    assert response.status_code == 400


async def test_workout_sets_are_private(client, alice, bob):
    data = await build_workout(client, alice)
    workout_id = data["workout"]["id"]
    program_exercise_id = data["program_exercise"]["id"]
    workout_set = await create_set(
        client, alice, workout_id, program_exercise_id
    )
    base = f"/scheduled-workouts/{workout_id}/sets"
    url = f"{base}/{workout_set['id']}"
    payload = {
        "program_exercise_id": program_exercise_id,
        "set_number": 5,
        "weight": 999,
        "reps": 1,
        "completed": True,
    }

    assert (await client.get(base, headers=bob)).status_code == 404
    assert (await client.post(base, json=payload, headers=bob)).status_code == 404
    assert (await client.get(url, headers=bob)).status_code == 404
    assert (await client.put(url, json=payload, headers=bob)).status_code == 404
    assert (
        await client.patch(url, json={"weight": 999}, headers=bob)
    ).status_code == 404
    assert (await client.delete(url, headers=bob)).status_code == 404

    # чужой подход нельзя достать и через свою тренировку
    bob_data = await build_workout(client, bob)
    response = await client.get(
        f"/scheduled-workouts/{bob_data['workout']['id']}/sets/{workout_set['id']}",
        headers=bob,
    )
    assert response.status_code == 404

    response = await client.get(base, headers=alice)
    assert response.json() == [workout_set]


async def test_workout_sets_require_auth(client, alice):
    data = await build_workout(client, alice)
    base = f"/scheduled-workouts/{data['workout']['id']}/sets"

    assert (await client.get(base)).status_code in (401, 403)
    assert (
        await client.post(
            base,
            json={
                "program_exercise_id": data["program_exercise"]["id"],
                "set_number": 1,
                "weight": 60,
                "reps": 8,
            },
        )
    ).status_code in (401, 403)


async def test_deleting_workout_deletes_its_sets(client, alice):
    data = await build_workout(client, alice)
    workout_id = data["workout"]["id"]
    await create_set(client, alice, workout_id, data["program_exercise"]["id"])

    response = await client.delete(
        f"/scheduled-workouts/{workout_id}", headers=alice
    )
    assert response.status_code == 204

    response = await client.get(
        f"/exercises/{data['exercise']['id']}/history", headers=alice
    )
    assert response.json() == []
