from tests.helpers import (
    build_workout,
    create_day,
    create_exercise,
    create_program,
    create_program_exercise,
    create_set,
    create_workout,
)


async def test_scheduled_workout_crud(client, alice):
    program = await create_program(client, alice)
    day = await create_day(client, alice, program["id"])
    other_day = await create_day(client, alice, program["id"], "День B", 2)

    workout = await create_workout(client, alice, program["id"], day["id"])
    assert workout == {
        "id": workout["id"],
        "program_id": program["id"],
        "program_day_id": day["id"],
        "program_name": program["name"],
        "day_name": day["name"],
        "scheduled_date": "2026-10-05",
        "status": "planned",
        "wellbeing": None,
        "difficulty": None,
        "feedback_comment": None,
        "feedback_at": None,
    }
    url = f"/scheduled-workouts/{workout['id']}"

    response = await client.get("/scheduled-workouts", headers=alice)
    assert response.json() == [workout]

    response = await client.get(url, headers=alice)
    assert response.status_code == 200
    assert response.json() == workout

    response = await client.put(
        url,
        json={
            "program_id": program["id"],
            "program_day_id": other_day["id"],
            "scheduled_date": "2026-10-07",
            "status": "completed",
        },
        headers=alice,
    )
    assert response.status_code == 200
    assert response.json()["program_day_id"] == other_day["id"]
    assert response.json()["scheduled_date"] == "2026-10-07"
    assert response.json()["status"] == "completed"

    response = await client.patch(url, json={"status": "skipped"}, headers=alice)
    assert response.status_code == 200
    assert response.json()["status"] == "skipped"
    assert response.json()["scheduled_date"] == "2026-10-07"

    response = await client.patch(
        url, json={"scheduled_date": "2026-10-09"}, headers=alice
    )
    assert response.json()["scheduled_date"] == "2026-10-09"
    assert response.json()["status"] == "skipped"

    response = await client.delete(url, headers=alice)
    assert response.status_code == 204
    assert (await client.get(url, headers=alice)).status_code == 404


async def test_scheduled_workout_validation(client, alice):
    program = await create_program(client, alice)
    day = await create_day(client, alice, program["id"])
    other_program = await create_program(client, alice, name="Другая")
    valid = {
        "program_id": program["id"],
        "program_day_id": day["id"],
        "scheduled_date": "2026-10-05",
    }

    for changes in (
        {"status": "done"},
        {"status": ""},
        {"scheduled_date": "не дата"},
        {"scheduled_date": "2026-13-40"},
    ):
        response = await client.post(
            "/scheduled-workouts", json={**valid, **changes}, headers=alice
        )
        assert response.status_code == 422, changes

    # несуществующая программа
    response = await client.post(
        "/scheduled-workouts", json={**valid, "program_id": 999}, headers=alice
    )
    assert response.status_code == 404

    # день из другой программы
    response = await client.post(
        "/scheduled-workouts",
        json={**valid, "program_id": other_program["id"]},
        headers=alice,
    )
    assert response.status_code == 404

    workout = await create_workout(client, alice, program["id"], day["id"])
    response = await client.patch(
        f"/scheduled-workouts/{workout['id']}",
        json={"status": "unknown"},
        headers=alice,
    )
    assert response.status_code == 422


async def test_scheduled_workout_filters(client, alice):
    program = await create_program(client, alice)
    other_program = await create_program(client, alice, name="Другая")
    day = await create_day(client, alice, program["id"])
    other_day = await create_day(client, alice, other_program["id"])

    await create_workout(client, alice, program["id"], day["id"], "2026-10-01")
    await create_workout(
        client, alice, program["id"], day["id"], "2026-10-10", "completed"
    )
    await create_workout(
        client, alice, other_program["id"], other_day["id"], "2026-10-20"
    )

    async def dates(**params):
        response = await client.get(
            "/scheduled-workouts", params=params, headers=alice
        )
        assert response.status_code == 200
        return [item["scheduled_date"] for item in response.json()]

    assert await dates() == ["2026-10-01", "2026-10-10", "2026-10-20"]
    # границы диапазона включаются
    assert await dates(date_from="2026-10-10") == ["2026-10-10", "2026-10-20"]
    assert await dates(date_to="2026-10-10") == ["2026-10-01", "2026-10-10"]
    assert await dates(date_from="2026-10-02", date_to="2026-10-19") == [
        "2026-10-10"
    ]
    assert await dates(status="completed") == ["2026-10-10"]
    assert await dates(program_id=other_program["id"]) == ["2026-10-20"]
    assert await dates(limit=1, offset=1) == ["2026-10-10"]

    response = await client.get(
        "/scheduled-workouts", params={"status": "done"}, headers=alice
    )
    assert response.status_code == 422


async def test_full_workout_view(client, alice):
    data = await build_workout(client, alice)
    workout_id = data["workout"]["id"]
    program_exercise = data["program_exercise"]

    second_exercise = await create_exercise(client, alice, name="Присед")
    second = await create_program_exercise(
        client,
        alice,
        data["program"]["id"],
        data["day"]["id"],
        second_exercise["id"],
        order_index=2,
    )

    await create_set(client, alice, workout_id, program_exercise["id"], 2, 62.5, 7)
    await create_set(client, alice, workout_id, program_exercise["id"], 1, 60, 8)

    response = await client.get(
        f"/scheduled-workouts/{workout_id}/full", headers=alice
    )
    assert response.status_code == 200
    body = response.json()

    assert body["id"] == workout_id
    assert body["program_name"] == data["program"]["name"]
    assert body["program_day_name"] == data["day"]["name"]
    assert body["scheduled_date"] == "2026-10-05"
    assert body["status"] == "planned"

    first_item, second_item = body["exercises"]
    assert first_item["program_exercise_id"] == program_exercise["id"]
    assert first_item["exercise"]["name"] == data["exercise"]["name"]
    assert first_item["sets"] == 3
    assert first_item["target_weight"] == 60
    assert [
        (s["set_number"], s["weight"], s["reps"])
        for s in first_item["performed_sets"]
    ] == [(1, 60, 8), (2, 62.5, 7)]

    assert second_item["program_exercise_id"] == second["id"]
    assert second_item["performed_sets"] == []


async def test_generate_schedule(client, alice):
    program = await create_program(client, alice)
    day_a = await create_day(client, alice, program["id"], "A", 1)
    day_b = await create_day(client, alice, program["id"], "B", 2)
    day_c = await create_day(client, alice, program["id"], "C", 3)

    # 2026-10-05 — понедельник. Пн/Ср/Пт, две недели.
    payload = {
        "program_id": program["id"],
        "start_date": "2026-10-05",
        "weeks": 2,
        "weekdays": [4, 0, 2],
    }

    response = await client.post(
        "/scheduled-workouts/generate", json=payload, headers=alice
    )
    assert response.status_code == 201
    created = response.json()

    assert [(w["scheduled_date"], w["program_day_id"]) for w in created] == [
        ("2026-10-05", day_a["id"]),
        ("2026-10-07", day_b["id"]),
        ("2026-10-09", day_c["id"]),
        ("2026-10-12", day_a["id"]),
        ("2026-10-14", day_b["id"]),
        ("2026-10-16", day_c["id"]),
    ]
    assert {w["status"] for w in created} == {"planned"}

    # повторный вызов не создаёт дубли на занятые даты
    response = await client.post(
        "/scheduled-workouts/generate", json=payload, headers=alice
    )
    assert response.status_code == 201
    assert response.json() == []

    response = await client.get("/scheduled-workouts", headers=alice)
    assert len(response.json()) == 6


async def test_generate_schedule_validation(client, alice, bob):
    program = await create_program(client, alice)
    valid = {
        "program_id": program["id"],
        "start_date": "2026-10-05",
        "weeks": 1,
        "weekdays": [0],
    }

    # в программе нет дней
    response = await client.post(
        "/scheduled-workouts/generate", json=valid, headers=alice
    )
    assert response.status_code == 400

    await create_day(client, alice, program["id"])

    for changes in (
        {"weeks": 0},
        {"weeks": 53},
        {"weekdays": []},
        {"weekdays": [7]},
        {"weekdays": [1, 1]},
    ):
        response = await client.post(
            "/scheduled-workouts/generate",
            json={**valid, **changes},
            headers=alice,
        )
        assert response.status_code == 422, changes

    # чужая программа
    response = await client.post(
        "/scheduled-workouts/generate", json=valid, headers=bob
    )
    assert response.status_code == 404


async def test_cannot_change_day_when_sets_are_logged(client, alice):
    data = await build_workout(client, alice)
    other_day = await create_day(
        client, alice, data["program"]["id"], "День B", 2
    )
    await create_set(
        client, alice, data["workout"]["id"], data["program_exercise"]["id"]
    )

    payload = {
        "program_id": data["program"]["id"],
        "program_day_id": other_day["id"],
        "scheduled_date": "2026-10-05",
        "status": "planned",
    }
    url = f"/scheduled-workouts/{data['workout']['id']}"

    response = await client.put(url, json=payload, headers=alice)
    assert response.status_code == 409

    # тот же день — можно (например, переносим дату)
    payload["program_day_id"] = data["day"]["id"]
    payload["scheduled_date"] = "2026-10-06"
    response = await client.put(url, json=payload, headers=alice)
    assert response.status_code == 200


async def test_scheduled_workouts_are_private(client, alice, bob):
    data = await build_workout(client, alice)
    url = f"/scheduled-workouts/{data['workout']['id']}"
    payload = {
        "program_id": data["program"]["id"],
        "program_day_id": data["day"]["id"],
        "scheduled_date": "2026-11-01",
        "status": "completed",
    }

    assert (await client.get("/scheduled-workouts", headers=bob)).json() == []
    assert (await client.get(url, headers=bob)).status_code == 404
    assert (await client.get(f"{url}/full", headers=bob)).status_code == 404
    assert (await client.put(url, json=payload, headers=bob)).status_code == 404
    assert (
        await client.patch(url, json={"status": "skipped"}, headers=bob)
    ).status_code == 404
    assert (await client.delete(url, headers=bob)).status_code == 404

    # нельзя запланировать тренировку по чужой программе
    response = await client.post(
        "/scheduled-workouts", json=payload, headers=bob
    )
    assert response.status_code == 404

    # нельзя перевесить свою тренировку на чужую программу
    bob_data = await build_workout(client, bob)
    response = await client.put(
        f"/scheduled-workouts/{bob_data['workout']['id']}",
        json=payload,
        headers=bob,
    )
    assert response.status_code == 404

    response = await client.get(url, headers=alice)
    assert response.json() == data["workout"]


async def test_scheduled_workouts_require_auth(client):
    assert (await client.get("/scheduled-workouts")).status_code in (401, 403)
    assert (await client.get("/scheduled-workouts/1")).status_code in (401, 403)
