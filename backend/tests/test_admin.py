import pytest_asyncio

from app.config import settings
from tests.helpers import build_workout, create_set, login, register_and_login


@pytest_asyncio.fixture
async def admin(client, monkeypatch):
    """Заголовки администратора: его email в ADMIN_EMAILS."""
    monkeypatch.setattr(settings, "admin_emails", ["boss@example.com"])

    return await register_and_login(client, "boss")


async def test_admin_flag_and_access(client, admin, alice):
    me = (await client.get("/auth/me", headers=admin)).json()
    assert me["is_admin"] is True
    assert (await client.get("/auth/me", headers=alice)).json()["is_admin"] is False

    for url in ("/admin/stats", "/admin/tables", "/admin/tables/users/rows"):
        assert (await client.get(url, headers=alice)).status_code == 403, url
        assert (await client.get(url, headers=admin)).status_code == 200, url


async def test_tables_and_columns(client, admin):
    tables = {t["name"]: t for t in (await client.get("/admin/tables", headers=admin)).json()}

    assert {"users", "exercises", "programs", "scheduled_workouts", "workout_sets"} <= set(tables)
    assert tables["users"]["count"] == 1

    users = {c["name"]: c for c in tables["users"]["columns"]}
    assert "password_hash" not in users
    assert users["password"]["kind"] == "password"
    assert users["role"]["readonly"] is True
    assert users["id"]["readonly"] is True

    workouts = {c["name"]: c for c in tables["scheduled_workouts"]["columns"]}
    assert workouts["status"]["choices"] == ["planned", "completed", "skipped"]
    assert workouts["user_id"]["references"] == "users"
    assert workouts["scheduled_date"]["kind"] == "date"


async def test_crud_exercise(client, admin):
    base = "/admin/tables/exercises/rows"

    response = await client.post(base, json={"name": "Тяга сумо"}, headers=admin)
    assert response.status_code == 201
    row = response.json()
    assert row["name"] == "Тяга сумо"
    assert row["created_by_user_id"] is None

    response = await client.post(base, json={"muscle_group": "Спина"}, headers=admin)
    assert response.status_code == 422

    response = await client.patch(
        f"{base}/{row['id']}",
        json={"muscle_group": "Ноги", "equipment": "Штанга"},
        headers=admin,
    )
    assert response.json()["muscle_group"] == "Ноги"

    found = (await client.get(base, params={"q": "сумо"}, headers=admin)).json()
    assert [r["id"] for r in found["rows"]] == [row["id"]]
    assert found["total"] == 1

    assert (await client.delete(f"{base}/{row['id']}", headers=admin)).status_code == 204
    assert (await client.get(f"{base}/{row['id']}", headers=admin)).status_code == 404


async def test_edit_users(client, admin, alice):
    rows = (await client.get("/admin/tables/users/rows", params={"q": "alice"}, headers=admin)).json()["rows"]
    [alice_row] = rows
    assert "password_hash" not in alice_row
    url = f"/admin/tables/users/rows/{alice_row['id']}"

    response = await client.patch(url, json={"username": "Алиса", "password": "new-secret-1"}, headers=admin)
    assert response.status_code == 200
    assert response.json()["username"] == "Алиса"
    assert (await login(client, "alice", "new-secret-1")).status_code == 200

    # Роль меняется только через COACH_EMAILS
    response = await client.patch(url, json={"role": "coach"}, headers=admin)
    assert response.json()["role"] == "user"

    assert (await client.patch(url, json={"password": "short"}, headers=admin)).status_code == 422

    # Создать пользователя с паролем
    response = await client.post(
        "/admin/tables/users/rows",
        json={"username": "новичок", "email": "new@example.com", "password": "password-123"},
        headers=admin,
    )
    assert response.status_code == 201
    assert (await client.post("/auth/login", json={"email": "new@example.com", "password": "password-123"})).status_code == 200

    response = await client.post(
        "/admin/tables/users/rows",
        json={"username": "без пароля", "email": "nopass@example.com"},
        headers=admin,
    )
    assert response.status_code == 422

    # Себя удалить нельзя, другого — можно
    me = (await client.get("/auth/me", headers=admin)).json()
    assert (await client.delete(f"/admin/tables/users/rows/{me['id']}", headers=admin)).status_code == 400
    assert (await client.delete(url, headers=admin)).status_code == 204


async def test_filters_types_and_conflicts(client, admin, alice):
    data = await build_workout(client, alice, "2026-10-05")
    await create_set(client, alice, data["workout"]["id"], data["program_exercise"]["id"], 1, 70, 6)
    user_id = data["program"]["user_id"]

    rows = (
        await client.get(
            "/admin/tables/scheduled_workouts/rows",
            params={"field": "user_id", "value": user_id},
            headers=admin,
        )
    ).json()
    assert rows["total"] == 1
    workout = rows["rows"][0]
    assert workout["scheduled_date"] == "2026-10-05"

    url = f"/admin/tables/scheduled_workouts/rows/{workout['id']}"
    response = await client.patch(
        url,
        json={"status": "completed", "scheduled_date": "2026-10-07", "wellbeing": 5},
        headers=admin,
    )
    assert response.status_code == 200
    assert response.json()["scheduled_date"] == "2026-10-07"

    assert (await client.patch(url, json={"status": "done"}, headers=admin)).status_code == 422
    assert (await client.patch(url, json={"wellbeing": "много"}, headers=admin)).status_code == 422
    # Ограничение базы: самочувствие 1–5
    assert (await client.patch(url, json={"wellbeing": 9}, headers=admin)).status_code == 409
    # Несуществующая связь
    assert (await client.patch(url, json={"user_id": 999}, headers=admin)).status_code == 409

    sets = (await client.get("/admin/tables/workout_sets/rows", headers=admin)).json()["rows"]
    set_url = f"/admin/tables/workout_sets/rows/{sets[0]['id']}"
    response = await client.patch(set_url, json={"weight": "72.5", "completed": False}, headers=admin)
    assert response.json()["weight"] == 72.5
    assert response.json()["completed"] is False

    # Упражнение с подходами удалить нельзя
    response = await client.delete(
        f"/admin/tables/exercises/rows/{data['exercise']['id']}", headers=admin
    )
    assert response.status_code == 409

    assert (await client.get("/admin/tables/nope/rows", headers=admin)).status_code == 404
    assert (await client.get("/admin/tables/users/rows", params={"sort": "password_hash"}, headers=admin)).status_code == 422


async def test_stats(client, admin, alice):
    stats = (await client.get("/admin/stats", headers=admin)).json()
    assert stats["counts"]["users"] == 2
    assert stats["new_users_week"] == 2
    assert stats["workouts_week"] == 0
