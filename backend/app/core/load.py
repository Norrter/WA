"""Нагрузка подхода с учётом веса тела.

У упражнения тип нагрузки:
- external   — вес снаряда (штанга, гантели, блок): нагрузка = вес;
- bodyweight — свой вес плюс отягощение (подтягивания, брусья):
               нагрузка = вес тела + доп. вес;
- assisted   — свой вес с облегчением (гравитрон, подтягивания
               с противовесом): нагрузка = вес тела − противовес.

В подходе хранится введённый вес (weight), вес тела на момент подхода
(body_weight) и посчитанная нагрузка (load). Вся статистика — объём,
рекорды, расчётный максимум — считается по load.
"""

from typing import Literal

LoadType = Literal["external", "bodyweight", "assisted"]

LOAD_TYPES: tuple[str, ...] = ("external", "bodyweight", "assisted")


def uses_body_weight(load_type: str) -> bool:
    return load_type in ("bodyweight", "assisted")


def compute_load(load_type: str, weight: float, body_weight: float | None) -> float:
    if load_type == "bodyweight":
        return round((body_weight or 0) + weight, 2)

    if load_type == "assisted":
        if body_weight is None:
            return 0.0
        return round(max(0.0, body_weight - weight), 2)

    return weight
