"""Питание: норма КБЖУ, продукты, дневник."""

from datetime import date, timedelta

from tests.test_coach import coach, make_client  # noqa: F401 — фикстуры


def day(offset: int) -> str:
    return (date.today() + timedelta(days=offset)).isoformat()


BODY = {"sex": "male", "age": 30, "height_cm": 180, "activity": "moderate", "goal": "maintain"}


async def test_calculate(client, alice):
    # Без веса — ошибка, с весом в запросе — расчёт
    response = await client.post("/nutrition/calculate", json=BODY, headers=alice)
    assert response.status_code == 400

    response = await client.post("/nutrition/calculate", json={**BODY, "weight": 80}, headers=alice)
    assert response.status_code == 200, response.text
    data = response.json()
    # 10*80 + 6.25*180 - 5*30 + 5 = 1780; ×1.55 = 2759
    assert data["bmr"] == 1780
    assert data["tdee"] == 2759
    assert data["kcal"] == 2760
    assert data["protein"] == 128
    assert data["fat"] == 80
    assert data["carbs"] == round((2760 - 128 * 4 - 80 * 9) / 4)

    # Похудение у женщины
    response = await client.post(
        "/nutrition/calculate",
        json={**BODY, "sex": "female", "goal": "lose", "weight": 60, "height_cm": 165},
        headers=alice,
    )
    data = response.json()
    assert data["bmr"] == round(600 + 6.25 * 165 - 150 - 161)
    assert data["protein"] == 120

    # Вес из журнала
    await client.post("/body-weight", json={"weight": 80}, headers=alice)
    response = await client.post("/nutrition/calculate", json=BODY, headers=alice)
    assert response.json()["weight"] == 80

    # Проверки
    response = await client.post("/nutrition/calculate", json={**BODY, "age": 5}, headers=alice)
    assert response.status_code == 422


async def test_profile(client, alice, bob):
    assert (await client.get("/nutrition/profile", headers=alice)).json() is None

    # Без веса тела сохранить расчётную норму нельзя
    response = await client.put("/nutrition/profile", json=BODY, headers=alice)
    assert response.status_code == 400

    await client.post("/body-weight", json={"weight": 80}, headers=alice)
    response = await client.put("/nutrition/profile", json=BODY, headers=alice)
    assert response.status_code == 200, response.text
    profile = response.json()
    assert profile["age"] == 30
    assert profile["targets"]["kcal"] == 2760
    assert profile["calculated"]["kcal"] == 2760

    # Своя норма
    targets = {"kcal": 2500, "protein": 150, "fat": 70, "carbs": 300}
    response = await client.put(
        "/nutrition/profile", json={**BODY, "goal": "lose", "targets": targets}, headers=alice
    )
    profile = response.json()
    assert profile["targets"] == targets
    assert profile["goal"] == "lose"
    assert profile["calculated"]["kcal"] == round(2759 * 0.85 / 10) * 10

    assert (await client.get("/nutrition/profile", headers=alice)).json()["targets"] == targets
    assert (await client.get("/nutrition/profile", headers=bob)).json() is None

    # Своя норма сохраняется и без веса тела
    response = await client.put(
        "/nutrition/profile", json={**BODY, "targets": targets}, headers=bob
    )
    assert response.status_code == 200
    assert response.json()["calculated"] is None


async def test_diary(client, alice, bob):
    # Запись с сохранением продукта — продукт на 100 г
    response = await client.post(
        "/nutrition/entries",
        json={
            "meal": "breakfast",
            "name": "Овсянка",
            "grams": 50,
            "kcal": 175,
            "protein": 6,
            "fat": 3.5,
            "carbs": 30,
            "save_food": True,
        },
        headers=alice,
    )
    assert response.status_code == 201, response.text
    oats = response.json()
    assert oats["date"] == day(0)
    assert oats["food_id"] is not None

    foods = (await client.get("/nutrition/foods", headers=alice)).json()
    assert [(f["name"], f["kcal"], f["protein"], f["fat"]) for f in foods] == [
        ("Овсянка", 350, 12, 7)
    ]

    # Без веса порции сохранить продукт нельзя
    response = await client.post(
        "/nutrition/entries",
        json={"meal": "snack", "name": "Батончик", "kcal": 200, "protein": 20, "fat": 7, "carbs": 15, "save_food": True},
        headers=alice,
    )
    assert response.status_code == 400

    # Просто запись без продукта
    response = await client.post(
        "/nutrition/entries",
        json={"meal": "lunch", "name": "Суп", "kcal": 250, "protein": 12, "fat": 9, "carbs": 28},
        headers=alice,
    )
    soup = response.json()
    assert soup["grams"] is None and soup["food_id"] is None

    # Вчерашняя запись
    await client.post(
        "/nutrition/entries",
        json={"date": day(-1), "meal": "dinner", "name": "Рис", "grams": 200, "kcal": 260, "protein": 5, "fat": 1, "carbs": 57},
        headers=alice,
    )

    today = (await client.get("/nutrition/day", headers=alice)).json()
    assert [e["name"] for e in today["entries"]] == ["Овсянка", "Суп"]
    assert today["totals"] == {"kcal": 425, "protein": 18, "fat": 12.5, "carbs": 58}
    assert today["targets"] is None

    # Изменить запись
    response = await client.patch(
        f"/nutrition/entries/{soup['id']}", json={"kcal": 300, "meal": "dinner"}, headers=alice
    )
    assert response.json()["kcal"] == 300
    assert response.json()["meal"] == "dinner"

    summary = (
        await client.get(
            "/nutrition/summary", params={"date_from": day(-7), "date_to": day(0)}, headers=alice
        )
    ).json()
    assert [(s["date"], s["entries"], s["kcal"]) for s in summary] == [
        (day(-1), 1, 260),
        (day(0), 2, 475),
    ]

    # Чужое недоступно
    assert (await client.get("/nutrition/day", headers=bob)).json()["entries"] == []
    assert (await client.delete(f"/nutrition/entries/{soup['id']}", headers=bob)).status_code == 404
    assert (await client.patch(f"/nutrition/entries/{soup['id']}", json={"kcal": 1}, headers=bob)).status_code == 404
    response = await client.post(
        "/nutrition/entries",
        json={"meal": "lunch", "name": "x", "kcal": 1, "protein": 0, "fat": 0, "carbs": 0, "food_id": oats["food_id"]},
        headers=bob,
    )
    assert response.status_code == 404
    assert (await client.get("/nutrition/foods", headers=bob)).json() == []

    # Удаление продукта не трогает записи дневника
    response = await client.delete(f"/nutrition/foods/{oats['food_id']}", headers=alice)
    assert response.status_code == 204
    today = (await client.get("/nutrition/day", headers=alice)).json()
    assert today["entries"][0]["name"] == "Овсянка"
    assert today["entries"][0]["food_id"] is None

    response = await client.delete(f"/nutrition/entries/{soup['id']}", headers=alice)
    assert response.status_code == 204
    assert len((await client.get("/nutrition/day", headers=alice)).json()["entries"]) == 1


async def test_foods(client, alice):
    for name in ["Творог 5%", "гречка", "Банан"]:
        response = await client.post(
            "/nutrition/foods",
            json={"name": name, "kcal": 100, "protein": 1, "fat": 1, "carbs": 1},
            headers=alice,
        )
        assert response.status_code == 201

    foods = (await client.get("/nutrition/foods", headers=alice)).json()
    assert [f["name"] for f in foods] == ["Банан", "гречка", "Творог 5%"]

    found = (await client.get("/nutrition/foods", params={"q": "твор"}, headers=alice)).json()
    assert [f["name"] for f in found] == ["Творог 5%"]

    response = await client.put(
        f"/nutrition/foods/{found[0]['id']}",
        json={"name": "Творог 9%", "kcal": 160, "protein": 16, "fat": 9, "carbs": 2},
        headers=alice,
    )
    assert response.json()["kcal"] == 160

    response = await client.post(
        "/nutrition/foods",
        json={"name": "", "kcal": 100, "protein": 1, "fat": 1, "carbs": 1},
        headers=alice,
    )
    assert response.status_code == 422


async def test_coach_sees_client_nutrition(client, coach, alice, bob):
    alice_id = await make_client(client, coach, alice)

    response = await client.get(f"/coach/clients/{alice_id}/nutrition", headers=coach)
    assert response.status_code == 200
    data = response.json()
    assert data["profile"] is None
    assert data["day"]["entries"] == [] and data["week"] == []

    await client.post("/body-weight", json={"weight": 80}, headers=alice)
    await client.put("/nutrition/profile", json=BODY, headers=alice)
    await client.post(
        "/nutrition/entries",
        json={"meal": "lunch", "name": "Суп", "kcal": 250, "protein": 12, "fat": 9, "carbs": 28},
        headers=alice,
    )
    await client.post(
        "/nutrition/entries",
        json={"date": day(-2), "meal": "dinner", "name": "Рис", "kcal": 300, "protein": 6, "fat": 1, "carbs": 65},
        headers=alice,
    )

    data = (await client.get(f"/coach/clients/{alice_id}/nutrition", headers=coach)).json()
    assert data["profile"]["targets"]["kcal"] == 2760
    assert data["day"]["totals"]["kcal"] == 250
    assert data["day"]["targets"]["kcal"] == 2760
    assert [(w["date"], w["kcal"]) for w in data["week"]] == [(day(-2), 300), (day(0), 250)]

    data = (
        await client.get(
            f"/coach/clients/{alice_id}/nutrition", params={"date": day(-2)}, headers=coach
        )
    ).json()
    assert [e["name"] for e in data["day"]["entries"]] == ["Рис"]

    # Не клиент — нельзя; обычный пользователь — нельзя
    bob_id = (await client.get("/auth/me", headers=bob)).json()["id"]
    assert (await client.get(f"/coach/clients/{bob_id}/nutrition", headers=coach)).status_code == 404
    assert (await client.get(f"/coach/clients/{alice_id}/nutrition", headers=bob)).status_code == 403
