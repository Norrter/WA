"""Правки плана во время тренировки: программа не меняется."""

from tests.helpers import build_workout, create_exercise, create_set


async def full(client, headers, workout_id):
    response = await client.get(f"/scheduled-workouts/{workout_id}/full", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def program_day(client, headers, data):
    response = await client.get(f"/programs/{data['program']['id']}", headers=headers)
    assert response.status_code == 200
    [day] = response.json()["days"]
    return day


async def test_change_plan_during_workout_keeps_program(client, alice):
    data = await build_workout(client, alice)
    workout_id = data["workout"]["id"]
    base = f"/scheduled-workouts/{workout_id}"

    # Подход до правок — по строке программы
    await create_set(client, alice, workout_id, data["program_exercise"]["id"], 1, 60, 8)

    detail = await full(client, alice, workout_id)
    assert detail["custom_plan"] is False
    assert detail["exercises"][0]["workout_exercise_id"] is None

    # Первое изменение копирует план в тренировку
    response = await client.post(f"{base}/customize", headers=alice)
    assert response.status_code == 200
    detail = response.json()
    assert detail["custom_plan"] is True
    [item] = detail["exercises"]
    item_id = item["workout_exercise_id"]
    assert item_id is not None
    assert item["program_exercise_id"] == data["program_exercise"]["id"]
    assert len(item["performed_sets"]) == 1

    # Повторный вызов ничего не дублирует
    detail = (await client.post(f"{base}/customize", headers=alice)).json()
    assert len(detail["exercises"]) == 1

    # Больше подходов
    response = await client.patch(f"{base}/exercises/{item_id}", json={"sets": 5}, headers=alice)
    assert response.status_code == 200
    assert response.json()["exercises"][0]["sets"] == 5

    # Новое упражнение в конец
    squat = await create_exercise(client, alice, "Присед")
    response = await client.post(
        f"{base}/exercises",
        json={"exercise_id": squat["id"], "sets": 2, "target_reps": 10},
        headers=alice,
    )
    assert response.status_code == 201
    detail = response.json()
    assert [e["exercise"]["name"] for e in detail["exercises"]] == ["Жим лёжа", "Присед"]
    added = detail["exercises"][1]
    assert added["program_exercise_id"] is None

    # Подход к добавленному упражнению
    response = await client.post(
        f"{base}/sets",
        json={"workout_exercise_id": added["workout_exercise_id"], "set_number": 1, "weight": 80, "reps": 10},
        headers=alice,
    )
    assert response.status_code == 201, response.text
    assert response.json()["exercise_id"] == squat["id"]

    # Повторный номер подхода в той же строке — конфликт
    response = await client.post(
        f"{base}/sets",
        json={"workout_exercise_id": added["workout_exercise_id"], "set_number": 1, "weight": 80, "reps": 10},
        headers=alice,
    )
    assert response.status_code == 409

    # Подход по старому способу (по строке программы) тоже попадает в свою строку
    await create_set(client, alice, workout_id, data["program_exercise"]["id"], 2, 60, 8)
    detail = await full(client, alice, workout_id)
    assert len(detail["exercises"][0]["performed_sets"]) == 2
    assert len(detail["exercises"][1]["performed_sets"]) == 1

    # Порядок
    response = await client.post(
        f"{base}/exercises/{added['workout_exercise_id']}/move",
        json={"direction": "up"},
        headers=alice,
    )
    assert [e["exercise"]["name"] for e in response.json()["exercises"]] == ["Присед", "Жим лёжа"]

    # Программа не изменилась
    day = await program_day(client, alice, data)
    assert [(e["exercise"]["name"], e["sets"]) for e in day["exercises"]] == [("Жим лёжа", 3)]

    # История и рекорды видят подход к добавленному упражнению
    response = await client.get(f"/exercises/{squat['id']}/history", headers=alice)
    assert [row["weight"] for row in response.json()] == [80]


async def test_replace_and_remove(client, alice):
    data = await build_workout(client, alice)
    workout_id = data["workout"]["id"]
    base = f"/scheduled-workouts/{workout_id}"
    detail = (await client.post(f"{base}/customize", headers=alice)).json()
    item_id = detail["exercises"][0]["workout_exercise_id"]

    # Заменить, пока подходов нет, — можно
    dips = await create_exercise(client, alice, "Брусья")
    response = await client.patch(
        f"{base}/exercises/{item_id}",
        json={"exercise_id": dips["id"]},
        headers=alice,
    )
    assert response.status_code == 200
    assert response.json()["exercises"][0]["exercise"]["name"] == "Брусья"

    # Подход к заменённому — без строки программы, с новым упражнением
    response = await client.post(
        f"{base}/sets",
        json={"workout_exercise_id": item_id, "set_number": 1, "weight": 0, "reps": 12},
        headers=alice,
    )
    body = response.json()
    assert body["exercise_id"] == dips["id"]
    assert body["program_exercise_id"] is None

    # После подхода заменить нельзя
    response = await client.patch(
        f"{base}/exercises/{item_id}",
        json={"exercise_id": data["exercise"]["id"]},
        headers=alice,
    )
    assert response.status_code == 409

    # Убрать — вместе с подходами
    response = await client.delete(f"{base}/exercises/{item_id}", headers=alice)
    assert response.status_code == 200
    assert response.json()["exercises"] == []
    response = await client.get(f"{base}/sets", headers=alice)
    assert response.json() == []

    # Программа прежняя
    day = await program_day(client, alice, data)
    assert [e["exercise"]["name"] for e in day["exercises"]] == ["Жим лёжа"]


async def test_validation_and_access(client, alice, bob):
    data = await build_workout(client, alice)
    workout_id = data["workout"]["id"]
    base = f"/scheduled-workouts/{workout_id}"

    # Чужая тренировка
    assert (await client.post(f"{base}/customize", headers=bob)).status_code == 404

    # Чужое собственное упражнение добавить нельзя
    bobs = await create_exercise(client, bob, "Секретное")
    response = await client.post(f"{base}/exercises", json={"exercise_id": bobs["id"]}, headers=alice)
    assert response.status_code == 404

    # Число подходов 1–20
    detail = (await client.post(f"{base}/customize", headers=alice)).json()
    item_id = detail["exercises"][0]["workout_exercise_id"]
    for sets in (0, 21):
        response = await client.patch(f"{base}/exercises/{item_id}", json={"sets": sets}, headers=alice)
        assert response.status_code == 422

    # Подход нужно привязать ровно к одному: строке программы или тренировки
    response = await client.post(
        f"{base}/sets",
        json={"set_number": 1, "weight": 10, "reps": 5},
        headers=alice,
    )
    assert response.status_code == 422

    # Строка другой тренировки не подходит
    other = await build_workout(client, alice, "2026-10-06")
    other_detail = (
        await client.post(f"/scheduled-workouts/{other['workout']['id']}/customize", headers=alice)
    ).json()
    response = await client.patch(
        f"{base}/exercises/{other_detail['exercises'][0]['workout_exercise_id']}",
        json={"sets": 2},
        headers=alice,
    )
    assert response.status_code == 404

    # Удаление тренировки убирает и её план
    response = await client.delete(base, headers=alice)
    assert response.status_code == 204
