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


async def test_exercise_history(client, alice):
    data = await build_workout(client, alice, "2026-10-05")
    exercise_id = data["exercise"]["id"]
    program_exercise_id = data["program_exercise"]["id"]
    later = await create_workout(
        client, alice, data["program"]["id"], data["day"]["id"], "2026-10-12"
    )

    await create_set(client, alice, data["workout"]["id"], program_exercise_id, 1, 60, 8)
    await create_set(client, alice, data["workout"]["id"], program_exercise_id, 2, 60, 7)
    await create_set(client, alice, later["id"], program_exercise_id, 1, 65, 6, False)

    url = f"/exercises/{exercise_id}/history"

    response = await client.get(url, headers=alice)
    assert response.status_code == 200
    # от новых к старым, внутри тренировки — по номеру подхода
    assert [
        (i["date"], i["set_number"], i["weight"], i["reps"], i["completed"])
        for i in response.json()
    ] == [
        ("2026-10-12", 1, 65, 6, False),
        ("2026-10-05", 1, 60, 8, True),
        ("2026-10-05", 2, 60, 7, True),
    ]

    response = await client.get(url, params={"date_to": "2026-10-05"}, headers=alice)
    assert len(response.json()) == 2

    response = await client.get(url, params={"date_from": "2026-10-06"}, headers=alice)
    assert len(response.json()) == 1

    response = await client.get(url, params={"limit": 1}, headers=alice)
    assert len(response.json()) == 1

    response = await client.get("/exercises/999/history", headers=alice)
    assert response.status_code == 404


async def test_exercise_records(client, alice):
    data = await build_workout(client, alice, "2026-10-05")
    exercise_id = data["exercise"]["id"]
    program_exercise_id = data["program_exercise"]["id"]
    workout_id = data["workout"]["id"]
    later = await create_workout(
        client, alice, data["program"]["id"], data["day"]["id"], "2026-10-12"
    )
    url = f"/exercises/{exercise_id}/records"

    # пока подходов нет
    response = await client.get(url, headers=alice)
    assert response.status_code == 200
    assert response.json() == {
        "exercise_id": exercise_id,
        "total_sets": 0,
        "total_reps": 0,
        "total_volume": 0,
        "last_performed": None,
        "max_weight": None,
        "best_estimated_1rm_set": None,
        "best_estimated_1rm": None,
    }

    await create_set(client, alice, workout_id, program_exercise_id, 1, 100, 1)
    await create_set(client, alice, workout_id, program_exercise_id, 2, 90, 10)
    await create_set(client, alice, later["id"], program_exercise_id, 1, 80, 5)
    # невыполненный подход в рекорды не идёт
    await create_set(client, alice, later["id"], program_exercise_id, 2, 200, 1, False)

    body = (await client.get(url, headers=alice)).json()

    assert body["total_sets"] == 3
    assert body["total_reps"] == 16
    assert body["total_volume"] == 100 * 1 + 90 * 10 + 80 * 5
    assert body["last_performed"] == "2026-10-12"
    assert body["max_weight"] == {"weight": 100, "reps": 1, "date": "2026-10-05"}
    # 90 кг × 10 по формуле Эпли = 90 × (1 + 10/30) = 120
    assert body["best_estimated_1rm_set"] == {
        "weight": 90,
        "reps": 10,
        "date": "2026-10-05",
    }
    assert body["best_estimated_1rm"] == 120


async def test_stats_summary(client, alice):
    data = await build_workout(client, alice, "2026-10-05")
    program_id, day_id = data["program"]["id"], data["day"]["id"]
    program_exercise_id = data["program_exercise"]["id"]

    done = await create_workout(
        client, alice, program_id, day_id, "2026-10-07", "completed"
    )
    await create_workout(client, alice, program_id, day_id, "2026-10-09", "skipped")
    await create_workout(client, alice, program_id, day_id, "2026-11-01", "completed")

    await create_set(client, alice, done["id"], program_exercise_id, 1, 50, 10)
    await create_set(client, alice, done["id"], program_exercise_id, 2, 50, 8)
    await create_set(client, alice, done["id"], program_exercise_id, 3, 50, 5, False)

    response = await client.get("/stats/summary", headers=alice)
    assert response.status_code == 200
    assert response.json() == {
        "date_from": None,
        "date_to": None,
        "workouts_planned": 1,
        "workouts_completed": 2,
        "workouts_skipped": 1,
        "total_sets": 2,
        "total_reps": 18,
        "total_volume": 900,
    }

    response = await client.get(
        "/stats/summary",
        params={"date_from": "2026-10-08", "date_to": "2026-10-31"},
        headers=alice,
    )
    assert response.json() == {
        "date_from": "2026-10-08",
        "date_to": "2026-10-31",
        "workouts_planned": 0,
        "workouts_completed": 0,
        "workouts_skipped": 1,
        "total_sets": 0,
        "total_reps": 0,
        "total_volume": 0,
    }


async def test_weekly_volume(client, alice):
    today = date.today()
    this_monday = today - timedelta(days=today.weekday())
    last_monday = this_monday - timedelta(weeks=1)

    data = await build_workout(client, alice, this_monday.isoformat())
    program_exercise_id = data["program_exercise"]["id"]
    previous = await create_workout(
        client,
        alice,
        data["program"]["id"],
        data["day"]["id"],
        (last_monday + timedelta(days=6)).isoformat(),  # воскресенье
    )
    too_old = await create_workout(
        client,
        alice,
        data["program"]["id"],
        data["day"]["id"],
        (this_monday - timedelta(weeks=3)).isoformat(),
    )

    await create_set(client, alice, data["workout"]["id"], program_exercise_id, 1, 100, 5)
    await create_set(client, alice, data["workout"]["id"], program_exercise_id, 2, 100, 5)
    await create_set(client, alice, previous["id"], program_exercise_id, 1, 40, 10)
    await create_set(client, alice, too_old["id"], program_exercise_id, 1, 500, 1)

    response = await client.get(
        "/stats/weekly-volume", params={"weeks": 3}, headers=alice
    )
    assert response.status_code == 200
    assert response.json() == [
        {
            "week_start": (this_monday - timedelta(weeks=2)).isoformat(),
            "workouts": 0,
            "sets": 0,
            "reps": 0,
            "volume": 0,
        },
        {
            "week_start": last_monday.isoformat(),
            "workouts": 1,
            "sets": 1,
            "reps": 10,
            "volume": 400,
        },
        {
            "week_start": this_monday.isoformat(),
            "workouts": 1,
            "sets": 2,
            "reps": 10,
            "volume": 1000,
        },
    ]

    response = await client.get(
        "/stats/weekly-volume", params={"weeks": 0}, headers=alice
    )
    assert response.status_code == 422


async def test_progress_is_private(client, alice, bob, shared_exercise):
    # Оба пользователя тренируют одно и то же общее упражнение
    async def train(headers, weight):
        program = await create_program(client, headers)
        day = await create_day(client, headers, program["id"])
        program_exercise = await create_program_exercise(
            client, headers, program["id"], day["id"], shared_exercise
        )
        workout = await create_workout(
            client, headers, program["id"], day["id"], date.today().isoformat()
        )
        await create_set(
            client, headers, workout["id"], program_exercise["id"], 1, weight, 5
        )

    await train(alice, 100)
    await train(bob, 40)

    history = (
        await client.get(f"/exercises/{shared_exercise}/history", headers=bob)
    ).json()
    assert [item["weight"] for item in history] == [40]

    records = (
        await client.get(f"/exercises/{shared_exercise}/records", headers=bob)
    ).json()
    assert records["max_weight"]["weight"] == 40
    assert records["total_sets"] == 1

    summary = (await client.get("/stats/summary", headers=bob)).json()
    assert summary["total_volume"] == 200

    weekly = (
        await client.get("/stats/weekly-volume", params={"weeks": 1}, headers=bob)
    ).json()
    assert weekly[0]["volume"] == 200

    # история по чужому личному упражнению недоступна
    private = await create_exercise(client, alice, name="Личное")
    response = await client.get(f"/exercises/{private['id']}/history", headers=bob)
    assert response.status_code == 404
    response = await client.get(f"/exercises/{private['id']}/records", headers=bob)
    assert response.status_code == 404


async def test_progress_requires_auth(client):
    for url in (
        "/exercises/1/history",
        "/exercises/1/records",
        "/stats/summary",
        "/stats/weekly-volume",
    ):
        assert (await client.get(url)).status_code in (401, 403), url
