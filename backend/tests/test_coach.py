from datetime import date, timedelta

import pytest_asyncio

from app.config import settings
from app.core.roles import sync_coach_roles
from app.database.session import AsyncSessionLocal
from tests.helpers import build_workout, create_set, register_and_login


@pytest_asyncio.fixture
async def coach(client, monkeypatch):
    """Заголовки тренера: его email в COACH_EMAILS."""
    monkeypatch.setattr(settings, "coach_emails", ["coach@example.com"])

    return await register_and_login(client, "coach")


async def me(client, headers):
    response = await client.get("/auth/me", headers=headers)
    assert response.status_code == 200

    return response.json()


async def finished_workout(client, headers, scheduled_date):
    """Тренировка с двумя выполненными подходами и одним невыполненным."""
    data = await build_workout(client, headers, scheduled_date)
    workout_id = data["workout"]["id"]
    program_exercise_id = data["program_exercise"]["id"]

    await create_set(client, headers, workout_id, program_exercise_id, 1, 100, 5)
    await create_set(client, headers, workout_id, program_exercise_id, 2, 100, 4)
    await create_set(
        client, headers, workout_id, program_exercise_id, 3, 110, 2, False
    )

    response = await client.patch(
        f"/scheduled-workouts/{workout_id}",
        json={"status": "completed"},
        headers=headers,
    )
    assert response.status_code == 200

    return data


async def test_roles_on_registration(client, alice, coach):
    assert (await me(client, alice))["role"] == "user"
    assert (await me(client, coach))["role"] == "coach"


async def test_regular_user_has_no_access(client, alice):
    for url in ("/coach/users", "/coach/users/1", "/coach/users/1/records"):
        response = await client.get(url, headers=alice)
        assert response.status_code == 403, url


async def test_users_list_with_stats(client, alice, bob, coach):
    await finished_workout(client, alice, "2026-10-05")

    response = await client.get("/coach/users", headers=coach)
    assert response.status_code == 200

    users = {item["username"]: item for item in response.json()}
    assert set(users) == {"alice", "bob", "coach"}
    assert users["coach"]["role"] == "coach"

    alice_stats = users["alice"]
    assert alice_stats["email"] == "alice@example.com"
    assert alice_stats["programs"] == 1
    assert alice_stats["workouts_completed"] == 1
    assert alice_stats["workouts_planned"] == 0
    # невыполненный подход не считается
    assert alice_stats["total_sets"] == 2
    assert alice_stats["total_volume"] == 900
    assert alice_stats["last_workout"] == "2026-10-05"

    bob_stats = users["bob"]
    assert bob_stats["programs"] == 0
    assert bob_stats["total_sets"] == 0
    assert bob_stats["total_volume"] == 0
    assert bob_stats["last_workout"] is None


async def test_users_list_period(client, alice, coach):
    await finished_workout(client, alice, "2026-10-05")

    response = await client.get(
        "/coach/users",
        params={"date_from": "2026-10-06", "date_to": "2026-10-31"},
        headers=coach,
    )
    alice_stats = next(i for i in response.json() if i["username"] == "alice")

    # за период ничего, но последняя тренировка видна всегда
    assert alice_stats["workouts_completed"] == 0
    assert alice_stats["total_sets"] == 0
    assert alice_stats["last_workout"] == "2026-10-05"


async def test_user_details(client, alice, coach):
    data = await finished_workout(client, alice, "2026-10-05")
    alice_id = (await me(client, alice))["id"]
    base = f"/coach/users/{alice_id}"

    response = await client.get(base, headers=coach)
    assert response.status_code == 200
    assert response.json()["username"] == "alice"

    response = await client.get(f"{base}/summary", headers=coach)
    assert response.status_code == 200
    summary = response.json()
    assert summary["workouts_completed"] == 1
    assert summary["total_sets"] == 2
    assert summary["total_reps"] == 9
    assert summary["total_volume"] == 900

    response = await client.get(f"{base}/records", headers=coach)
    assert response.status_code == 200
    [record] = response.json()
    assert record["exercise_id"] == data["exercise"]["id"]
    assert record["exercise_name"] == data["exercise"]["name"]
    assert record["max_weight"] == {"weight": 100, "reps": 5, "date": "2026-10-05"}
    assert record["total_sets"] == 2

    response = await client.get(f"{base}/workouts", headers=coach)
    assert response.status_code == 200
    [workout] = response.json()
    assert workout["id"] == data["workout"]["id"]
    assert workout["status"] == "completed"
    assert workout["program_name"] == data["program"]["name"]
    assert workout["day_name"] == data["day"]["name"]
    assert workout["sets_completed"] == 2
    assert workout["volume"] == 900


async def test_weekly_volume_of_user(client, alice, coach):
    today = date.today()
    await finished_workout(client, alice, today.isoformat())
    alice_id = (await me(client, alice))["id"]

    response = await client.get(
        f"/coach/users/{alice_id}/weekly-volume",
        params={"weeks": 4},
        headers=coach,
    )
    assert response.status_code == 200
    weeks = response.json()
    assert len(weeks) == 4
    assert weeks[-1]["week_start"] == (
        today - timedelta(days=today.weekday())
    ).isoformat()
    assert weeks[-1]["volume"] == 900
    assert [week["volume"] for week in weeks[:-1]] == [0, 0, 0]


async def test_workouts_are_newest_first(client, alice, coach):
    await finished_workout(client, alice, "2026-10-05")
    await finished_workout(client, alice, "2026-10-08")
    alice_id = (await me(client, alice))["id"]

    response = await client.get(
        f"/coach/users/{alice_id}/workouts",
        params={"limit": 1},
        headers=coach,
    )
    assert [w["scheduled_date"] for w in response.json()] == ["2026-10-08"]

    response = await client.get(
        f"/coach/users/{alice_id}/workouts",
        params={"date_to": "2026-10-06"},
        headers=coach,
    )
    assert [w["scheduled_date"] for w in response.json()] == ["2026-10-05"]


async def test_unknown_user(client, coach):
    for suffix in ("", "/summary", "/weekly-volume", "/records", "/workouts"):
        response = await client.get(f"/coach/users/999{suffix}", headers=coach)
        assert response.status_code == 404, suffix


async def test_sync_roles_on_startup(client, alice, coach, monkeypatch):
    # Список поменяли: alice стала тренером, coach — обычным пользователем
    monkeypatch.setattr(settings, "coach_emails", ["alice@example.com"])

    async with AsyncSessionLocal() as session:
        await sync_coach_roles(session)

    assert (await me(client, alice))["role"] == "coach"
    assert (await me(client, coach))["role"] == "user"

    response = await client.get("/coach/users", headers=coach)
    assert response.status_code == 403


async def test_email_change_updates_role(client, alice, monkeypatch):
    monkeypatch.setattr(settings, "coach_emails", ["boss@example.com"])

    response = await client.patch(
        "/users/me",
        json={"email": "Boss@example.com"},
        headers=alice,
    )
    assert response.status_code == 200
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
