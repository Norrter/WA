"""Короткие функции для подготовки данных в тестах."""

PASSWORD = "correct-horse-battery"


async def register(client, name: str, password: str = PASSWORD):
    return await client.post(
        "/users",
        json={
            "email": f"{name}@example.com",
            "username": name,
            "password": password,
        },
    )


async def login(client, name: str, password: str = PASSWORD):
    return await client.post(
        "/auth/login",
        json={"email": f"{name}@example.com", "password": password},
    )


async def register_and_login(client, name: str) -> dict:
    """Создать пользователя и вернуть заголовок Authorization."""
    response = await register(client, name)
    assert response.status_code == 201, response.text

    response = await login(client, name)
    assert response.status_code == 200, response.text

    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def create_exercise(client, headers, name="Жим лёжа", **fields):
    response = await client.post(
        "/exercises",
        json={"name": name, **fields},
        headers=headers,
    )
    assert response.status_code == 200, response.text

    return response.json()


async def create_program(client, headers, name="Сплит"):
    response = await client.post(
        "/programs",
        json={"name": name, "description": "Описание"},
        headers=headers,
    )
    assert response.status_code == 200, response.text

    return response.json()


async def create_day(client, headers, program_id, name="День A", order_index=1):
    response = await client.post(
        f"/programs/{program_id}/days",
        json={"name": name, "order_index": order_index},
        headers=headers,
    )
    assert response.status_code == 200, response.text

    return response.json()


async def create_program_exercise(
    client,
    headers,
    program_id,
    day_id,
    exercise_id,
    order_index=1,
    **fields,
):
    payload = {
        "exercise_id": exercise_id,
        "order_index": order_index,
        "sets": 3,
        "target_reps": 8,
        "target_weight": 60,
        "rest_seconds": 120,
        "notes": None,
        **fields,
    }

    response = await client.post(
        f"/programs/{program_id}/days/{day_id}/exercises",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 200, response.text

    return response.json()


async def create_workout(
    client,
    headers,
    program_id,
    day_id,
    scheduled_date="2026-10-05",
    status="planned",
):
    response = await client.post(
        "/scheduled-workouts",
        json={
            "program_id": program_id,
            "program_day_id": day_id,
            "scheduled_date": scheduled_date,
            "status": status,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text

    return response.json()


async def create_set(
    client,
    headers,
    workout_id,
    program_exercise_id,
    set_number=1,
    weight=60,
    reps=8,
    completed=True,
):
    response = await client.post(
        f"/scheduled-workouts/{workout_id}/sets",
        json={
            "program_exercise_id": program_exercise_id,
            "set_number": set_number,
            "weight": weight,
            "reps": reps,
            "completed": completed,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text

    return response.json()


async def build_workout(client, headers, scheduled_date="2026-10-05"):
    """Полная цепочка: упражнение -> программа -> день ->
    упражнение в дне -> тренировка на дату."""
    exercise = await create_exercise(client, headers)
    program = await create_program(client, headers)
    day = await create_day(client, headers, program["id"])
    program_exercise = await create_program_exercise(
        client,
        headers,
        program["id"],
        day["id"],
        exercise["id"],
    )
    workout = await create_workout(
        client,
        headers,
        program["id"],
        day["id"],
        scheduled_date,
    )

    return {
        "exercise": exercise,
        "program": program,
        "day": day,
        "program_exercise": program_exercise,
        "workout": workout,
    }
