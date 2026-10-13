"""Защита истории, программы тренера, оценка тренировки, обзор периода."""

from datetime import date, timedelta

from tests.helpers import (
    build_workout,
    create_day,
    create_exercise,
    create_program,
    create_program_exercise,
    create_set,
    create_workout,
)
from tests.test_coach import (  # noqa: F401 — фикстуры
    coach,
    coach2,
    complete,
    days_ago,
    make_client,
)


# ----- История не пропадает при изменении плана -----


async def test_removing_exercise_from_plan_keeps_sets(client, alice):
    data = await build_workout(client, alice)
    workout_id = data["workout"]["id"]
    item = data["program_exercise"]
    await create_set(client, alice, workout_id, item["id"], 1, 80, 5)
    await complete(client, alice, workout_id)

    response = await client.delete(
        f"/programs/{data['program']['id']}/days/{data['day']['id']}/exercises/{item['id']}",
        headers=alice,
    )
    assert response.status_code == 204

    # Подход остался: в истории, рекордах и на экране тренировки
    exercise_id = data["exercise"]["id"]
    history = (await client.get(f"/exercises/{exercise_id}/history", headers=alice)).json()
    assert [(h["weight"], h["reps"]) for h in history] == [(80, 5)]

    records = (await client.get(f"/exercises/{exercise_id}/records", headers=alice)).json()
    assert records["total_sets"] == 1

    full = (await client.get(f"/scheduled-workouts/{workout_id}/full", headers=alice)).json()
    [exercise] = full["exercises"]
    assert exercise["program_exercise_id"] is None
    assert exercise["exercise"]["id"] == exercise_id
    assert [s["weight"] for s in exercise["performed_sets"]] == [80]

    # Упражнение с подходами удалить нельзя
    response = await client.delete(f"/exercises/{exercise_id}", headers=alice)
    assert response.status_code == 409


async def test_deleting_day_keeps_done_workouts(client, alice):
    data = await build_workout(client, alice, "2026-10-05")
    program_id = data["program"]["id"]
    day_id = data["day"]["id"]
    await create_set(client, alice, data["workout"]["id"], data["program_exercise"]["id"])
    await complete(client, alice, data["workout"]["id"])

    future = await create_workout(client, alice, program_id, day_id, "2026-12-01")

    response = await client.delete(f"/programs/{program_id}/days/{day_id}", headers=alice)
    assert response.status_code == 204

    workouts = (await client.get("/scheduled-workouts", headers=alice)).json()
    assert [w["id"] for w in workouts] == [data["workout"]["id"]]
    [done] = workouts
    assert done["program_day_id"] is None
    assert done["day_name"] == data["day"]["name"]
    assert future["id"] not in [w["id"] for w in workouts]

    full = (
        await client.get(f"/scheduled-workouts/{done['id']}/full", headers=alice)
    ).json()
    assert full["program_day_name"] == data["day"]["name"]
    assert len(full["exercises"]) == 1


async def test_deleting_program_keeps_history(client, alice):
    data = await build_workout(client, alice, "2026-10-05")
    await create_set(client, alice, data["workout"]["id"], data["program_exercise"]["id"], 1, 100, 3)
    await complete(client, alice, data["workout"]["id"])

    # Переименовали программу перед удалением — в истории новое имя
    await client.patch(
        f"/programs/{data['program']['id']}",
        json={"name": "Сила"},
        headers=alice,
    )
    response = await client.delete(f"/programs/{data['program']['id']}", headers=alice)
    assert response.status_code == 204

    [workout] = (await client.get("/scheduled-workouts", headers=alice)).json()
    assert workout["program_id"] is None
    assert workout["program_name"] == "Сила"

    summary = (await client.get("/stats/summary", headers=alice)).json()
    assert summary["workouts_completed"] == 1
    assert summary["total_volume"] == 300


# ----- Программы тренера -----


async def coach_program(client, coach_headers):
    """Шаблон тренера: программа с одним днём и упражнением."""
    exercise = await create_exercise(client, coach_headers, "Жим тренера")
    program = await create_program(client, coach_headers, "Программа тренера")
    day = await create_day(client, coach_headers, program["id"])
    await create_program_exercise(
        client, coach_headers, program["id"], day["id"], exercise["id"]
    )

    return program


async def test_assign_program(client, coach, alice):
    alice_id = await make_client(client, coach, alice)
    template = await coach_program(client, coach)
    monday = date.today() + timedelta(days=7 - date.today().weekday())

    response = await client.post(
        f"/coach/clients/{alice_id}/programs",
        json={
            "program_id": template["id"],
            "schedule": {"start_date": monday.isoformat(), "weeks": 2, "weekdays": [0, 3]},
        },
        headers=coach,
    )
    assert response.status_code == 201
    assigned_id = response.json()["program_id"]
    assert response.json()["workouts_created"] == 4

    # У клиента — копия от тренера, только для чтения
    [program] = (await client.get("/programs", headers=alice)).json()
    assert program["id"] == assigned_id
    assert program["can_edit"] is False
    assert program["assigned_by"]["username"] == "coach"
    assert program["source_program_id"] == template["id"]

    workouts = (await client.get("/scheduled-workouts", headers=alice)).json()
    assert len(workouts) == 4

    response = await client.patch(
        f"/programs/{assigned_id}", json={"name": "Моя"}, headers=alice
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Program is managed by your coach"

    response = await client.post(
        f"/programs/{assigned_id}/days",
        json={"name": "Лишний", "order_index": 5},
        headers=alice,
    )
    assert response.status_code == 403

    # Заниматься по ней можно
    full = (
        await client.get(f"/scheduled-workouts/{workouts[0]['id']}/full", headers=alice)
    ).json()
    assert full["coach_name"] == "coach"
    await create_set(
        client, alice, workouts[0]["id"], full["exercises"][0]["program_exercise_id"]
    )

    # Тренер правит назначенную программу, шаблон не меняется
    response = await client.patch(
        f"/programs/{assigned_id}", json={"name": "Для Алисы"}, headers=coach
    )
    assert response.status_code == 200
    assert response.json()["can_edit"] is True

    template_now = (await client.get(f"/programs/{template['id']}", headers=coach)).json()
    assert template_now["name"] == "Программа тренера"

    listed = (await client.get(f"/coach/clients/{alice_id}/programs", headers=coach)).json()
    assert [(p["name"], p["can_edit"]) for p in listed] == [("Для Алисы", True)]


async def test_client_creates_own_copy(client, coach, alice):
    alice_id = await make_client(client, coach, alice)
    template = await coach_program(client, coach)
    assigned = (
        await client.post(
            f"/coach/clients/{alice_id}/programs",
            json={"program_id": template["id"]},
            headers=coach,
        )
    ).json()

    response = await client.post(f"/programs/{assigned['program_id']}/copy", headers=alice)
    assert response.status_code == 201
    copy = response.json()
    assert copy["can_edit"] is True
    assert copy["assigned_by"] is None

    response = await client.patch(f"/programs/{copy['id']}", json={"name": "Своя"}, headers=alice)
    assert response.status_code == 200

    # Тренер копию видит, но не меняет
    response = await client.patch(f"/programs/{copy['id']}", json={"name": "Х"}, headers=coach)
    assert response.status_code == 403


async def test_coach_program_rules(client, coach, coach2, alice, bob):
    alice_id = await make_client(client, coach, alice)
    foreign = await coach_program(client, coach2)

    # Чужую программу назначить нельзя
    response = await client.post(
        f"/coach/clients/{alice_id}/programs",
        json={"program_id": foreign["id"]},
        headers=coach,
    )
    assert response.status_code == 404

    # Своего клиента — можно смотреть; чужого — нет
    own = await create_program(client, alice, "Своя у Алисы")
    assert (await client.get(f"/programs/{own['id']}", headers=coach)).status_code == 200
    bob_program = await create_program(client, bob, "Боба")
    assert (await client.get(f"/programs/{bob_program['id']}", headers=coach)).status_code == 404

    # Готовый шаблон назначить можно
    template = await create_program(client, coach, "Пустая")
    response = await client.post(
        f"/coach/clients/{alice_id}/programs",
        json={
            "program_id": template["id"],
            "schedule": {"start_date": "2026-11-02", "weeks": 1, "weekdays": [0]},
        },
        headers=coach,
    )
    # Без дней разложить нельзя
    assert response.status_code == 400


async def test_after_end_program_becomes_clients(client, coach, alice):
    alice_id = await make_client(client, coach, alice)
    template = await coach_program(client, coach)
    assigned = (
        await client.post(
            f"/coach/clients/{alice_id}/programs",
            json={"program_id": template["id"]},
            headers=coach,
        )
    ).json()
    program_id = assigned["program_id"]

    response = await client.post(
        f"/coach/clients/{alice_id}/programs/{program_id}/schedule",
        json={"start_date": "2026-11-02", "weeks": 1, "weekdays": [0, 2]},
        headers=coach,
    )
    assert response.json()["workouts_created"] == 2

    await client.post("/coaching/end", headers=alice)

    [program] = (await client.get("/programs", headers=alice)).json()
    assert program["can_edit"] is True
    response = await client.patch(f"/programs/{program_id}", json={"name": "Теперь моя"}, headers=alice)
    assert response.status_code == 200

    assert (await client.get(f"/programs/{program_id}", headers=coach)).status_code == 404


# ----- Оценка после тренировки -----


async def test_workout_feedback(client, coach, alice):
    alice_id = await make_client(client, coach, alice)
    data = await build_workout(client, alice, days_ago(1))
    workout_id = data["workout"]["id"]
    url = f"/scheduled-workouts/{workout_id}"

    for bad in ({"wellbeing": 0}, {"wellbeing": 6}, {"difficulty": 11}):
        assert (await client.patch(url, json=bad, headers=alice)).status_code == 422

    response = await client.patch(
        url,
        json={
            "status": "completed",
            "wellbeing": 4,
            "difficulty": 8,
            "feedback_comment": "  Тяжело, но хорошо  ",
        },
        headers=alice,
    )
    assert response.status_code == 200
    workout = response.json()
    assert (workout["wellbeing"], workout["difficulty"]) == (4, 8)
    assert workout["feedback_comment"] == "Тяжело, но хорошо"
    assert workout["feedback_at"] is not None

    [item] = (await client.get(f"/coach/clients/{alice_id}/workouts", headers=coach)).json()
    assert (item["wellbeing"], item["difficulty"]) == (4, 8)
    assert item["feedback_comment"] == "Тяжело, но хорошо"

    card = (
        await client.get(
            f"/coach/clients/{alice_id}",
            params={"date_from": days_ago(27), "date_to": days_ago(0)},
            headers=coach,
        )
    ).json()
    assert card["metrics"]["avg_wellbeing"] == 4
    assert card["metrics"]["avg_difficulty"] == 8

    # Комментарий можно стереть
    response = await client.patch(url, json={"feedback_comment": ""}, headers=alice)
    assert response.json()["feedback_comment"] is None


# ----- Обзор периода -----


async def test_overview(client, coach, alice):
    alice_id = await make_client(client, coach, alice)

    # Прошлый период: 100 кг × 5, текущий: 110 кг × 5
    data = await build_workout(client, alice, days_ago(40))
    await create_set(client, alice, data["workout"]["id"], data["program_exercise"]["id"], 1, 100, 5)
    await complete(client, alice, data["workout"]["id"])

    now = await create_workout(
        client, alice, data["program"]["id"], data["day"]["id"], days_ago(3)
    )
    await create_set(client, alice, now["id"], data["program_exercise"]["id"], 1, 110, 5)
    await complete(client, alice, now["id"])
    await create_workout(
        client, alice, data["program"]["id"], data["day"]["id"], days_ago(2), "skipped"
    )

    params = {"date_from": days_ago(27), "date_to": days_ago(0)}
    overview = (await client.get("/stats/overview", params=params, headers=alice)).json()

    assert overview["previous_to"] == days_ago(28)
    assert overview["previous_from"] == days_ago(55)
    assert overview["current"]["workouts_completed"] == 1
    assert overview["current"]["workouts_skipped"] == 1
    assert overview["current"]["adherence"] == 0.5
    assert overview["current"]["new_records"] == 1
    assert overview["previous"]["workouts_completed"] == 1
    assert overview["strength_change"] == 0.1

    [key] = overview["key_exercises"]
    assert key["name"] == data["exercise"]["name"]
    assert key["change"] == 0.1
    assert key["sets"] == 1

    # То же у тренера
    coach_view = (
        await client.get(f"/coach/clients/{alice_id}/overview", params=params, headers=coach)
    ).json()
    assert coach_view["strength_change"] == 0.1

    history = (
        await client.get(
            f"/coach/clients/{alice_id}/exercises/{data['exercise']['id']}/history",
            headers=coach,
        )
    ).json()
    assert [h["weight"] for h in history] == [110, 100]

    # Значения по умолчанию — последние 4 недели
    default = (await client.get("/stats/overview", headers=alice)).json()
    assert default["date_from"] == days_ago(27)

    response = await client.get(
        "/stats/overview",
        params={"date_from": days_ago(0), "date_to": days_ago(5)},
        headers=alice,
    )
    assert response.status_code == 422


async def test_schedule_order(client, coach, alice):
    alice_id = await make_client(client, coach, alice)
    data = await build_workout(client, alice, days_ago(-5))
    await create_workout(client, alice, data["program"]["id"], data["day"]["id"], days_ago(-1))

    items = (
        await client.get(
            f"/coach/clients/{alice_id}/workouts",
            params={"date_from": days_ago(0), "order": "asc"},
            headers=coach,
        )
    ).json()
    assert [i["scheduled_date"] for i in items] == [days_ago(-1), days_ago(-5)]


async def test_all_records(client, alice):
    data = await build_workout(client, alice, days_ago(3))
    await create_set(client, alice, data["workout"]["id"], data["program_exercise"]["id"], 1, 90, 5)

    [record] = (await client.get("/stats/records", headers=alice)).json()
    assert record["exercise_name"] == data["exercise"]["name"]
    assert record["max_weight"]["weight"] == 90
