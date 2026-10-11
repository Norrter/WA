from tests.helpers import PASSWORD, build_workout, create_set, login, register


async def test_health(client):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": True}


async def test_register_returns_user_without_password(client):
    response = await register(client, "alice")

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["username"] == "alice"
    assert "password" not in body
    assert "password_hash" not in body


async def test_register_duplicate_email_and_username(client):
    await register(client, "alice")

    response = await client.post(
        "/users",
        json={
            "email": "alice@example.com",
            "username": "other",
            "password": PASSWORD,
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"

    response = await client.post(
        "/users",
        json={
            "email": "other@example.com",
            "username": "alice",
            "password": PASSWORD,
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Username already registered"


async def test_register_validation(client):
    # короткий пароль
    assert (await register(client, "alice", password="short")).status_code == 422

    # некорректный email
    response = await client.post(
        "/users",
        json={"email": "not-an-email", "username": "alice", "password": PASSWORD},
    )
    assert response.status_code == 422

    # слишком короткое имя
    response = await client.post(
        "/users",
        json={"email": "a@example.com", "username": "a", "password": PASSWORD},
    )
    assert response.status_code == 422


async def test_login_and_me(client):
    await register(client, "alice")

    response = await login(client, "alice")
    assert response.status_code == 200
    tokens = response.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"] and tokens["refresh_token"]

    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["username"] == "alice"


async def test_login_wrong_credentials(client):
    await register(client, "alice")

    assert (await login(client, "alice", "wrong-password")).status_code == 401
    assert (await login(client, "nobody")).status_code == 401


async def test_protected_route_requires_token(client):
    assert (await client.get("/auth/me")).status_code in (401, 403)

    response = await client.get(
        "/auth/me",
        headers={"Authorization": "Bearer not-a-token"},
    )
    assert response.status_code == 401


async def test_refresh_gives_working_tokens(client):
    await register(client, "alice")
    tokens = (await login(client, "alice")).json()

    response = await client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 200
    new_tokens = response.json()

    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
    )
    assert response.status_code == 200


async def test_token_types_are_not_interchangeable(client):
    await register(client, "alice")
    tokens = (await login(client, "alice")).json()

    # refresh-токен не подходит для обычных запросов
    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
    )
    assert response.status_code == 401

    # access-токен нельзя обменять на новую пару
    response = await client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["access_token"]},
    )
    assert response.status_code == 401


async def test_update_profile(client, alice, bob):
    response = await client.patch(
        "/users/me",
        json={"username": "alice2"},
        headers=alice,
    )
    assert response.status_code == 200
    assert response.json()["username"] == "alice2"
    assert response.json()["email"] == "alice@example.com"

    # занятое имя и занятый email
    response = await client.patch(
        "/users/me", json={"username": "bob"}, headers=alice
    )
    assert response.status_code == 409

    response = await client.patch(
        "/users/me", json={"email": "bob@example.com"}, headers=alice
    )
    assert response.status_code == 409

    # обнулить обязательное поле нельзя
    response = await client.patch(
        "/users/me", json={"username": None}, headers=alice
    )
    assert response.status_code == 422


async def test_change_password(client, alice):
    response = await client.post(
        "/users/me/password",
        json={"current_password": "wrong", "new_password": "new-password-123"},
        headers=alice,
    )
    assert response.status_code == 400

    response = await client.post(
        "/users/me/password",
        json={"current_password": PASSWORD, "new_password": "short"},
        headers=alice,
    )
    assert response.status_code == 422

    response = await client.post(
        "/users/me/password",
        json={"current_password": PASSWORD, "new_password": "new-password-123"},
        headers=alice,
    )
    assert response.status_code == 204

    assert (await login(client, "alice", PASSWORD)).status_code == 401
    assert (await login(client, "alice", "new-password-123")).status_code == 200


async def test_delete_account_removes_everything(client, alice):
    data = await build_workout(client, alice)
    await create_set(
        client, alice, data["workout"]["id"], data["program_exercise"]["id"]
    )

    response = await client.delete("/users/me", headers=alice)
    assert response.status_code == 204

    # токен удалённого пользователя больше не работает
    assert (await client.get("/auth/me", headers=alice)).status_code == 401
    assert (await login(client, "alice")).status_code == 401

    # тот же email можно зарегистрировать заново, и данных там нет
    assert (await register(client, "alice")).status_code == 201
    tokens = (await login(client, "alice")).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert (await client.get("/programs", headers=headers)).json() == []
    assert (await client.get("/exercises", headers=headers)).json() == []


async def test_cors_allows_configured_frontend_only(client):
    response = await client.options(
        "/programs",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"

    response = await client.options(
        "/programs",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in response.headers


async def test_openapi_schema_is_generated(client):
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/scheduled-workouts/{scheduled_workout_id}/full" in paths
    assert "/exercises/{exercise_id}/history" in paths
