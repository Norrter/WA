"""Заметки для клиента и комментарии тренера к тренировкам."""

from tests.test_coach import (  # noqa: F401 — фикстуры
    coach,
    coach2,
    days_ago,
    finished_workout,
    make_client,
)


async def shared_notes(client, headers):
    response = await client.get("/coaching/notes", headers=headers)
    assert response.status_code == 200

    return response.json()


async def test_shared_notes(client, coach, coach2, alice, bob):
    alice_id = await make_client(client, coach, alice)
    base = f"/coach/clients/{alice_id}/notes"

    private = (await client.post(base, json={"text": "Колено"}, headers=coach)).json()
    assert private["shared"] is False

    shared = (
        await client.post(
            base,
            json={"text": "Пей больше воды", "shared": True},
            headers=coach,
        )
    ).json()
    assert shared["shared"] is True

    # Клиент видит только заметки «Видна клиенту»
    notes = await shared_notes(client, alice)
    assert [n["text"] for n in notes] == ["Пей больше воды"]
    assert "shared" not in notes[0]
    assert await shared_notes(client, bob) == []

    # Видимость меняется отдельно от текста
    response = await client.patch(
        f"/coach/notes/{private['id']}",
        json={"shared": True},
        headers=coach,
    )
    assert response.status_code == 200
    assert response.json()["text"] == "Колено"
    assert len(await shared_notes(client, alice)) == 2

    response = await client.patch(
        f"/coach/notes/{shared['id']}",
        json={"shared": False},
        headers=coach,
    )
    assert [n["text"] for n in await shared_notes(client, alice)] == ["Колено"]

    # После завершения сотрудничества заметки клиенту не видны
    await client.post("/coaching/end", headers=alice)
    assert await shared_notes(client, alice) == []

    # Новый тренер не показывает заметки прежнего
    await make_client(client, coach2, alice)
    assert await shared_notes(client, alice) == []


async def test_coach_opens_and_comments_workout(client, coach, coach2, alice, bob):
    alice_id = await make_client(client, coach, alice)
    data = await finished_workout(client, alice, days_ago(2))
    workout_id = data["workout"]["id"]
    url = f"/coach/clients/{alice_id}/workouts/{workout_id}"

    response = await client.get(url, headers=coach)
    assert response.status_code == 200
    detail = response.json()
    assert detail["status"] == "completed"
    [exercise] = detail["exercises"]
    assert len(exercise["performed_sets"]) == 3
    assert detail["coach_comment"] is None

    response = await client.put(
        url + "/comment",
        json={"text": "  Отлично, в следующий раз +2,5 кг  "},
        headers=coach,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["coach_comment"] == "Отлично, в следующий раз +2,5 кг"
    assert body["coach_comment_author"] == "coach"

    # Клиент видит комментарий в своей тренировке
    response = await client.get(f"/scheduled-workouts/{workout_id}/full", headers=alice)
    detail = response.json()
    assert detail["coach_comment"] == "Отлично, в следующий раз +2,5 кг"
    assert detail["coach_comment_author"] == "coach"
    assert detail["coach_comment_at"] is not None

    # и в списке тренировок у тренера
    response = await client.get(f"/coach/clients/{alice_id}/workouts", headers=coach)
    assert response.json()[0]["coach_comment"] == "Отлично, в следующий раз +2,5 кг"

    # Пустой текст удаляет комментарий
    response = await client.put(url + "/comment", json={"text": " "}, headers=coach)
    assert response.json()["coach_comment"] is None
    response = await client.get(f"/scheduled-workouts/{workout_id}/full", headers=alice)
    assert response.json()["coach_comment"] is None

    # Чужой тренер и чужая тренировка недоступны
    response = await client.get(url, headers=coach2)
    assert response.status_code == 404

    bob_data = await finished_workout(client, bob, days_ago(1))
    response = await client.get(
        f"/coach/clients/{alice_id}/workouts/{bob_data['workout']['id']}",
        headers=coach,
    )
    assert response.status_code == 404

    response = await client.put(
        f"/coach/clients/{alice_id}/workouts/{bob_data['workout']['id']}/comment",
        json={"text": "Нельзя"},
        headers=coach,
    )
    assert response.status_code == 404

    # Сам клиент комментарий тренера поставить не может
    response = await client.put(url + "/comment", json={"text": "Сам себе"}, headers=alice)
    assert response.status_code == 403
