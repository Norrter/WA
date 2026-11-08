import pytest_asyncio

from app.database.session import AsyncSessionLocal
from app.models import Program, ProgramDay, ProgramExercise
from tests.helpers import (
    create_day,
    create_exercise,
    create_program,
    create_program_exercise,
    create_workout,
)


@pytest_asyncio.fixture
async def template(shared_exercise):
    """Общая программа без владельца: один день с одним упражнением."""
    async with AsyncSessionLocal() as session:
        program = Program(
            user_id=None,
            name="Готовый сплит",
            description="Шаблон для всех",
            days=[
                ProgramDay(
                    name="День 1",
                    order_index=1,
                    exercises=[
                        ProgramExercise(
                            exercise_id=shared_exercise,
                            order_index=1,
                            sets=4,
                            target_reps=8,
                            target_reps_max=12,
                            notes="Суперсет",
                        )
                    ],
                )
            ],
        )

        session.add(program)
        await session.commit()

        return program.id


async def test_templates_are_listed_for_everyone(client, alice, bob, template):
    for headers in (alice, bob):
        response = await client.get("/programs/templates", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert [item["id"] for item in body] == [template]

        exercise = body[0]["days"][0]["exercises"][0]
        assert exercise["target_reps"] == 8
        assert exercise["target_reps_max"] == 12
        assert exercise["notes"] == "Суперсет"

    # в списке своих программ шаблона нет
    assert (await client.get("/programs", headers=alice)).json() == []


async def test_templates_require_auth(client):
    assert (await client.get("/programs/templates")).status_code in (401, 403)


async def test_template_cannot_be_changed_or_scheduled(client, alice, template):
    url = f"/programs/{template}"

    assert (await client.get(url, headers=alice)).status_code == 404
    assert (
        await client.put(url, json={"name": "Моё"}, headers=alice)
    ).status_code == 404
    assert (
        await client.patch(url, json={"name": "Моё"}, headers=alice)
    ).status_code == 404
    assert (await client.delete(url, headers=alice)).status_code == 404
    assert (
        await client.post(
            f"{url}/days", json={"name": "X", "order_index": 9}, headers=alice
        )
    ).status_code == 404

    response = await client.post(
        "/scheduled-workouts/generate",
        json={
            "program_id": template,
            "start_date": "2026-10-05",
            "weeks": 1,
            "weekdays": [0],
        },
        headers=alice,
    )
    assert response.status_code == 404

    # шаблон на месте и не изменился
    templates = (await client.get("/programs/templates", headers=alice)).json()
    assert templates[0]["name"] == "Готовый сплит"
    assert len(templates[0]["days"]) == 1


async def test_copy_template(client, alice, template):
    response = await client.post(f"/programs/{template}/copy", headers=alice)
    assert response.status_code == 201
    copy_id = response.json()["id"]
    assert copy_id != template

    copy = (await client.get(f"/programs/{copy_id}", headers=alice)).json()
    assert copy["name"] == "Готовый сплит"
    assert copy["description"] == "Шаблон для всех"
    assert [day["name"] for day in copy["days"]] == ["День 1"]

    item = copy["days"][0]["exercises"][0]
    assert (item["sets"], item["target_reps"], item["target_reps_max"]) == (4, 8, 12)
    assert item["notes"] == "Суперсет"

    # копию можно менять и планировать, шаблон при этом не меняется
    day_id = copy["days"][0]["id"]
    response = await client.patch(
        f"/programs/{copy_id}/days/{day_id}/exercises/{item['id']}",
        json={"sets": 2},
        headers=alice,
    )
    assert response.status_code == 200

    await client.patch(f"/programs/{copy_id}", json={"name": "Мой сплит"}, headers=alice)
    await create_workout(client, alice, copy_id, day_id)

    templates = (await client.get("/programs/templates", headers=alice)).json()
    assert templates[0]["name"] == "Готовый сплит"
    assert templates[0]["days"][0]["exercises"][0]["sets"] == 4

    programs = (await client.get("/programs", headers=alice)).json()
    assert [program["name"] for program in programs] == ["Мой сплит"]


async def test_copy_own_program_but_not_foreign(client, alice, bob):
    exercise = await create_exercise(client, alice)
    program = await create_program(client, alice, name="Своя")
    day = await create_day(client, alice, program["id"])
    await create_program_exercise(
        client, alice, program["id"], day["id"], exercise["id"]
    )

    response = await client.post(f"/programs/{program['id']}/copy", headers=bob)
    assert response.status_code == 404

    response = await client.post(f"/programs/{program['id']}/copy", headers=alice)
    assert response.status_code == 201

    programs = (await client.get("/programs", headers=alice)).json()
    assert [item["name"] for item in programs] == ["Своя", "Своя"]

    assert (
        await client.post("/programs/999/copy", headers=alice)
    ).status_code == 404


async def test_reps_range(client, alice):
    exercise = await create_exercise(client, alice)
    program = await create_program(client, alice)
    day = await create_day(client, alice, program["id"])
    base = f"/programs/{program['id']}/days/{day['id']}/exercises"

    item = await create_program_exercise(
        client,
        alice,
        program["id"],
        day["id"],
        exercise["id"],
        target_reps=8,
        target_reps_max=12,
    )
    assert (item["target_reps"], item["target_reps_max"]) == (8, 12)

    # верхняя граница меньше нижней
    response = await client.post(
        base,
        json={
            "exercise_id": exercise["id"],
            "order_index": 2,
            "sets": 3,
            "target_reps": 12,
            "target_reps_max": 8,
        },
        headers=alice,
    )
    assert response.status_code == 422

    # верхняя граница без нижней
    response = await client.post(
        base,
        json={
            "exercise_id": exercise["id"],
            "order_index": 2,
            "sets": 3,
            "target_reps": None,
            "target_reps_max": 8,
        },
        headers=alice,
    )
    assert response.status_code == 422

    # PATCH проверяет итоговое значение: 8..6 недопустимо
    response = await client.patch(
        f"{base}/{item['id']}", json={"target_reps_max": 6}, headers=alice
    )
    assert response.status_code == 422

    response = await client.patch(
        f"{base}/{item['id']}", json={"target_reps_max": None}, headers=alice
    )
    assert response.status_code == 200
    assert response.json()["target_reps_max"] is None

    # диапазон виден на экране тренировки
    await client.patch(
        f"{base}/{item['id']}", json={"target_reps_max": 10}, headers=alice
    )
    workout = await create_workout(client, alice, program["id"], day["id"])
    full = (
        await client.get(f"/scheduled-workouts/{workout['id']}/full", headers=alice)
    ).json()
    assert full["exercises"][0]["target_reps_max"] == 10
