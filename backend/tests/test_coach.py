from datetime import date, timedelta

import pytest_asyncio

from app.config import settings
from app.core.roles import sync_coach_roles
from app.database.session import AsyncSessionLocal
from app.services.coaching import improved_records
from tests.helpers import (
    build_workout,
    create_set,
    create_workout,
    register,
    register_and_login,
)


@pytest_asyncio.fixture
async def coach(client, monkeypatch):
    """Заголовки тренера: его email в COACH_EMAILS."""
    monkeypatch.setattr(
        settings,
        "coach_emails",
        ["coach@example.com", "coach2@example.com"],
    )

    return await register_and_login(client, "coach")


@pytest_asyncio.fixture
async def coach2(client, coach):
    return await register_and_login(client, "coach2")


async def me(client, headers):
    response = await client.get("/auth/me", headers=headers)
    assert response.status_code == 200

    return response.json()


async def invite(client, coach_headers, email, expected=201):
    response = await client.post(
        "/coach/clients",
        json={"email": email},
        headers=coach_headers,
    )
    assert response.status_code == expected, response.text

    return response.json()


async def pending(client, headers):
    response = await client.get("/coaching", headers=headers)
    assert response.status_code == 200

    return response.json()


async def make_client(client, coach_headers, client_headers):
    """Тренер добавляет клиента: вернуть id клиента."""
    user = await me(client, client_headers)
    link = await invite(client, coach_headers, user["email"])
    assert link["status"] == "active"

    return user["id"]


async def complete(client, headers, workout_id):
    response = await client.patch(
        f"/scheduled-workouts/{workout_id}",
        json={"status": "completed"},
        headers=headers,
    )
    assert response.status_code == 200


async def finished_workout(client, headers, scheduled_date, weight=100):
    """Тренировка с двумя выполненными подходами и одним невыполненным."""
    data = await build_workout(client, headers, scheduled_date)
    workout_id = data["workout"]["id"]
    program_exercise_id = data["program_exercise"]["id"]

    await create_set(client, headers, workout_id, program_exercise_id, 1, weight, 5)
    await create_set(client, headers, workout_id, program_exercise_id, 2, weight, 4)
    await create_set(
        client, headers, workout_id, program_exercise_id, 3, weight + 10, 2, False
    )
    await complete(client, headers, workout_id)

    return data


def days_ago(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


# ----- Роли -----


async def test_roles_on_registration(client, alice, coach):
    assert (await me(client, alice))["role"] == "user"
    assert (await me(client, coach))["role"] == "coach"


async def test_regular_user_has_no_access(client, alice):
    for url in ("/coach/clients", "/coach/clients/1", "/coach/clients/1/records"):
        response = await client.get(url, headers=alice)
        assert response.status_code == 403, url


async def test_sync_roles_on_startup(client, alice, coach, monkeypatch):
    monkeypatch.setattr(settings, "coach_emails", ["alice@example.com"])

    async with AsyncSessionLocal() as session:
        await sync_coach_roles(session)

    assert (await me(client, alice))["role"] == "coach"
    assert (await me(client, coach))["role"] == "user"

    response = await client.get("/coach/clients", headers=coach)
    assert response.status_code == 403


async def test_email_change_updates_role(client, alice, monkeypatch):
    monkeypatch.setattr(settings, "coach_emails", ["boss@example.com"])

    response = await client.patch(
        "/users/me",
        json={"email": "Boss@example.com"},
        headers=alice,
    )
    assert response.json()["role"] == "coach"

    response = await client.patch(
        "/users/me",
        json={"email": "alice@example.com"},
        headers=alice,
    )
    assert response.json()["role"] == "user"


def test_coach_emails_parsing():
    parse = type(settings).split_coach_emails

    assert parse(" A@x.com, b@y.com ,") == ["a@x.com", "b@y.com"]
    assert parse('["C@x.com"]') == ["c@x.com"]
    assert parse("") == []


# ----- Добавление клиентов -----


async def test_coach_adds_client_directly(client, coach, alice):
    link = await invite(client, coach, "Alice@Example.com")
    assert link["status"] == "active"
    assert link["invited_email"] == "alice@example.com"
    assert link["client"]["username"] == "alice"
    assert link["responded_at"] is not None

    # Подтверждение клиента не нужно: тренер сразу видит его данные
    alice_id = link["client"]["id"]
    response = await client.get(f"/coach/clients/{alice_id}", headers=coach)
    assert response.status_code == 200
    assert response.json()["client"]["username"] == "alice"

    state = await pending(client, alice)
    assert state["coach"]["coach"]["username"] == "coach"
    assert state["coach"]["since"] is not None
    assert "invitations" not in state

    response = await client.get("/coach/clients", headers=coach)
    [item] = response.json()
    assert item["status"] == "active"
    # тренировок ещё не было — «Проверить»
    assert item["metrics"]["flag"] == "check"


async def test_add_before_registration(client, coach, coach2):
    link = await invite(client, coach, "newbie@example.com")
    assert link["client"] is None
    assert link["status"] == "invited"

    # Email уже занят ожиданием у другого тренера
    await invite(client, coach, "newbie@example.com", expected=409)
    response = await client.post(
        "/coach/clients",
        json={"email": "newbie@example.com"},
        headers=coach2,
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Client already has a coach"

    # После регистрации человек сразу становится клиентом
    newbie = await register_and_login(client, "newbie")
    state = await pending(client, newbie)
    assert state["coach"]["coach"]["username"] == "coach"

    response = await client.get("/coach/clients", headers=coach)
    [item] = response.json()
    assert item["status"] == "active"
    assert item["client"]["username"] == "newbie"


async def test_waiting_coach_attached_on_email_change(client, coach, alice):
    await invite(client, coach, "alice.new@example.com")

    response = await client.patch(
        "/users/me",
        json={"email": "alice.new@example.com"},
        headers=alice,
    )
    assert response.status_code == 200
    assert (await pending(client, alice))["coach"]["coach"]["username"] == "coach"


async def test_add_rules(client, coach, coach2, alice):
    await invite(client, coach, "coach@example.com", expected=400)

    await invite(client, coach, "alice@example.com")

    # У клиента уже есть тренер
    response = await client.post(
        "/coach/clients",
        json={"email": "alice@example.com"},
        headers=coach2,
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Client already has a coach"

    response = await client.post(
        "/coach/clients",
        json={"email": "alice@example.com"},
        headers=coach,
    )
    assert response.json()["detail"] == "Already your client"

    # Подтверждать больше нечего
    response = await client.post("/coaching/invitations/1/accept", headers=alice)
    assert response.status_code in (404, 405)


async def test_cancel_waiting(client, coach, alice):
    link = await invite(client, coach, "ghost@example.com")

    response = await client.delete(f"/coach/invitations/{link['id']}", headers=coach)
    assert response.status_code == 204

    # Активного клиента так не убрать — только завершить сотрудничество
    active = await invite(client, coach, "alice@example.com")
    response = await client.delete(f"/coach/invitations/{active['id']}", headers=coach)
    assert response.status_code == 409

    # После отмены email свободен
    await invite(client, coach, "ghost@example.com")


async def test_end_by_coach_keeps_history(client, coach, alice):
    alice_id = await make_client(client, coach, alice)
    await finished_workout(client, alice, "2026-10-05")

    response = await client.post(f"/coach/clients/{alice_id}/end", headers=coach)
    assert response.status_code == 200
    assert response.json()["status"] == "ended"

    response = await client.get(f"/coach/clients/{alice_id}/records", headers=coach)
    assert response.status_code == 404

    # История у клиента осталась
    response = await client.get("/stats/summary", headers=alice)
    assert response.json()["workouts_completed"] == 1
    assert (await pending(client, alice))["coach"] is None

    # Можно пригласить снова
    await invite(client, coach, "alice@example.com")


async def test_end_by_client(client, coach, coach2, alice):
    await make_client(client, coach, alice)

    response = await client.post("/coaching/end", headers=alice)
    assert response.status_code == 200
    assert response.json()["coach"] is None

    response = await client.post("/coaching/end", headers=alice)
    assert response.status_code == 404

    # Теперь можно работать с другим тренером
    await make_client(client, coach2, alice)


async def test_coach_sees_only_own_clients(client, coach, coach2, alice, bob):
    alice_id = await make_client(client, coach, alice)
    bob_id = await make_client(client, coach2, bob)

    for suffix in ("", "/summary", "/weekly-volume", "/records", "/workouts", "/notes"):
        response = await client.get(f"/coach/clients/{bob_id}{suffix}", headers=coach)
        assert response.status_code == 404, suffix

        response = await client.get(f"/coach/clients/{alice_id}{suffix}", headers=coach)
        assert response.status_code == 200, suffix

    response = await client.get("/coach/clients", headers=coach)
    assert [item["client"]["username"] for item in response.json()] == ["alice"]


# ----- Показатели -----


async def test_client_data(client, coach, alice):
    alice_id = await make_client(client, coach, alice)
    data = await finished_workout(client, alice, "2026-10-05")
    base = f"/coach/clients/{alice_id}"

    summary = (await client.get(f"{base}/summary", headers=coach)).json()
    assert summary["workouts_completed"] == 1
    assert summary["total_sets"] == 2
    assert summary["total_volume"] == 900

    [record] = (await client.get(f"{base}/records", headers=coach)).json()
    assert record["exercise_name"] == data["exercise"]["name"]
    assert record["max_weight"] == {"weight": 100, "reps": 5, "date": "2026-10-05"}

    [workout] = (await client.get(f"{base}/workouts", headers=coach)).json()
    assert workout["status"] == "completed"
    assert workout["sets_completed"] == 2
    assert workout["volume"] == 900

    weeks = (
        await client.get(f"{base}/weekly-volume", params={"weeks": 4}, headers=coach)
    ).json()
    assert len(weeks) == 4


async def test_metrics_and_flags(client, coach, alice):
    alice_id = await make_client(client, coach, alice)

    data = await finished_workout(client, alice, days_ago(2))
    program_id = data["program"]["id"]
    day_id = data["day"]["id"]

    # Пропущенная, не отмеченная и будущая тренировки
    await create_workout(client, alice, program_id, day_id, days_ago(4), "skipped")
    await create_workout(client, alice, program_id, day_id, days_ago(3))
    upcoming = await create_workout(client, alice, program_id, day_id, days_ago(-2))

    response = await client.get(
        f"/coach/clients/{alice_id}",
        params={"date_from": days_ago(27), "date_to": days_ago(0)},
        headers=coach,
    )
    metrics = response.json()["metrics"]

    assert metrics["workouts_completed"] == 1
    assert metrics["workouts_skipped"] == 1
    assert metrics["workouts_missed"] == 1
    assert metrics["workouts_upcoming"] == 0
    assert metrics["adherence"] == round(1 / 3, 3)
    assert metrics["total_sets"] == 2
    assert metrics["last_workout"] == days_ago(2)
    assert metrics["days_since_last_workout"] == 2
    assert metrics["next_workout"]["id"] == upcoming["id"]
    assert metrics["next_workout"]["day_name"] == data["day"]["name"]
    assert metrics["flag"] == "check"
    assert metrics["reasons"] == ["low_adherence"]


async def test_flag_inactive(client, coach, alice):
    await make_client(client, coach, alice)
    await finished_workout(client, alice, days_ago(9))

    [item] = (await client.get("/coach/clients", headers=coach)).json()
    assert item["metrics"]["flag"] == "check"
    assert "inactive" in item["metrics"]["reasons"]


async def repeat_exercise(client, headers, data, days, weight):
    """Ещё одна выполненная тренировка с тем же упражнением."""
    workout = await create_workout(
        client, headers, data["program"]["id"], data["day"]["id"], days_ago(days)
    )
    await create_set(
        client, headers, workout["id"], data["program_exercise"]["id"], 1, weight, 5
    )
    await complete(client, headers, workout["id"])


async def test_flag_progress_and_on_track(client, coach, alice, bob):
    # alice: давно 100 кг, недавно снова 100 кг — застой
    await make_client(client, coach, alice)
    alice_data = await finished_workout(client, alice, days_ago(40))
    await repeat_exercise(client, alice, alice_data, 1, 100)

    # bob: недавно побил рекорд
    await make_client(client, coach, bob)
    bob_data = await finished_workout(client, bob, days_ago(40))
    await repeat_exercise(client, bob, bob_data, 1, 110)

    response = await client.get(
        "/coach/clients",
        params={"date_from": days_ago(27), "date_to": days_ago(0)},
        headers=coach,
    )
    metrics = {
        item["client"]["username"]: item["metrics"] for item in response.json()
    }

    assert metrics["alice"]["flag"] == "progress"
    assert metrics["alice"]["reasons"] == ["stagnation"]
    assert metrics["alice"]["new_records"] == 0
    assert metrics["bob"]["flag"] == "on_track"
    assert metrics["bob"]["new_records"] == 1
    assert metrics["bob"]["adherence"] == 1


def test_improved_records():
    day = date(2026, 10, 1)
    sets = [
        (1, day - timedelta(days=10), 100),
        (1, day + timedelta(days=1), 105),
        # первое выполнение — не рекорд
        (2, day + timedelta(days=2), 50),
        (3, day - timedelta(days=10), 80),
        (3, day + timedelta(days=3), 80),
    ]

    assert improved_records(sets, day, day + timedelta(days=7)) == 1


# ----- Заметки -----


async def test_notes(client, coach, coach2, alice):
    alice_id = await make_client(client, coach, alice)
    base = f"/coach/clients/{alice_id}/notes"

    response = await client.post(base, json={"text": "  Жалуется на колено  "}, headers=coach)
    assert response.status_code == 201
    note = response.json()
    assert note["text"] == "Жалуется на колено"

    response = await client.post(base, json={"text": "   "}, headers=coach)
    assert response.status_code == 422

    response = await client.patch(
        f"/coach/notes/{note['id']}",
        json={"text": "Колено в порядке"},
        headers=coach,
    )
    assert response.json()["text"] == "Колено в порядке"

    # Другой тренер заметку не видит и не меняет
    response = await client.patch(
        f"/coach/notes/{note['id']}",
        json={"text": "Чужое"},
        headers=coach2,
    )
    assert response.status_code == 404

    response = await client.get(base, headers=coach)
    assert [n["text"] for n in response.json()] == ["Колено в порядке"]

    response = await client.delete(f"/coach/notes/{note['id']}", headers=coach)
    assert response.status_code == 204
    assert (await client.get(base, headers=coach)).json() == []


async def test_unknown_client(client, coach):
    for suffix in ("", "/summary", "/weekly-volume", "/records", "/workouts", "/notes"):
        response = await client.get(f"/coach/clients/999{suffix}", headers=coach)
        assert response.status_code == 404, suffix


async def test_account_deletion_removes_links(client, coach, alice):
    await make_client(client, coach, alice)

    response = await client.delete("/users/me", headers=alice)
    assert response.status_code == 204

    response = await client.get("/coach/clients", headers=coach)
    assert response.json() == []


async def test_plain_registration(client):
    response = await register(client, "plain")
    assert response.status_code == 201
    assert response.json()["role"] == "user"
