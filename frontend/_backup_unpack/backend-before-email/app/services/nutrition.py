"""Расчёт нормы калорий и БЖУ по антропометрии.

1. Основной обмен — формула Миффлина — Сан Жеора:
   мужчины: 10 × вес + 6,25 × рост − 5 × возраст + 5
   женщины: 10 × вес + 6,25 × рост − 5 × возраст − 161
2. Расход за день = основной обмен × коэффициент активности.
3. Цель: похудение −15 %, поддержание как есть, набор +10 %.
4. Белок и жиры — граммы на кг веса, углеводы — оставшиеся калории.
"""

from datetime import date

ACTIVITY = {
    # нет тренировок, сидячая работа
    "minimal": 1.2,
    # 1–3 тренировки в неделю
    "light": 1.375,
    # 3–5 тренировок в неделю
    "moderate": 1.55,
    # 6–7 тренировок в неделю
    "high": 1.725,
    # тяжёлый физический труд или по две тренировки в день
    "extreme": 1.9,
}

GOAL_FACTOR = {"lose": 0.85, "maintain": 1.0, "gain": 1.1}

# граммов на кг веса тела
PROTEIN_PER_KG = {"lose": 2.0, "maintain": 1.6, "gain": 1.8}
FAT_PER_KG = {"lose": 0.9, "maintain": 1.0, "gain": 1.0}


def age_from_birth_year(birth_year: int) -> int:
    return max(0, date.today().year - birth_year)


def calculate(
    *,
    sex: str,
    age: int,
    height_cm: float,
    weight: float,
    activity: str,
    goal: str,
) -> dict:
    bmr = 10 * weight + 6.25 * height_cm - 5 * age + (5 if sex == "male" else -161)
    tdee = bmr * ACTIVITY[activity]
    kcal = round(tdee * GOAL_FACTOR[goal] / 10) * 10

    protein = round(PROTEIN_PER_KG[goal] * weight)
    fat = round(FAT_PER_KG[goal] * weight)
    carbs = max(0, round((kcal - protein * 4 - fat * 9) / 4))

    return {
        "bmr": round(bmr),
        "tdee": round(tdee),
        "kcal": kcal,
        "protein": protein,
        "fat": fat,
        "carbs": carbs,
    }
