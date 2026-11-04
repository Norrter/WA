// Нагрузка с учётом веса тела — так же, как на сервере (app/core/load.py)

import type { LoadType } from "../api/types";
import { formatNumber } from "./format";

export const LOAD_TYPES: { value: LoadType; label: string; hint: string }[] = [
  {
    value: "external",
    label: "Вес снаряда",
    hint: "Штанга, гантели, блок, тренажёр: нагрузка — это вес, который вы поднимаете.",
  },
  {
    value: "bodyweight",
    label: "Свой вес + отягощение",
    hint: "Подтягивания, брусья, отжимания: нагрузка = вес тела + доп. вес (пояс, жилет).",
  },
  {
    value: "assisted",
    label: "Свой вес с облегчением",
    hint: "Гравитрон, подтягивания с противовесом: нагрузка = вес тела − противовес.",
  },
];

export function usesBodyWeight(type: LoadType | undefined): boolean {
  return type === "bodyweight" || type === "assisted";
}

export function computeLoad(
  type: LoadType | undefined,
  weight: number,
  bodyWeight: number | null | undefined,
): number {
  if (type === "bodyweight") return Math.round(((bodyWeight ?? 0) + weight) * 100) / 100;
  if (type === "assisted") {
    if (bodyWeight === null || bodyWeight === undefined) return 0;
    return Math.max(0, Math.round((bodyWeight - weight) * 100) / 100);
  }
  return weight;
}

// Подпись поля веса в тренировке
export function weightLabel(type: LoadType | undefined): string {
  if (type === "bodyweight") return "Доп. вес, кг";
  if (type === "assisted") return "Противовес, кг";
  return "Вес, кг";
}

// Введённый вес так, как его понимает человек: «+10», «−20», «свой»
export function enteredText(type: LoadType | undefined, weight: number): string {
  if (type === "bodyweight") return weight === 0 ? "свой вес" : `+${formatNumber(weight)}`;
  if (type === "assisted") return `−${formatNumber(weight)}`;
  return formatNumber(weight);
}

// «80 − 20 = 60 кг»
export function loadFormula(
  type: LoadType | undefined,
  weight: number,
  bodyWeight: number | null | undefined,
): string {
  if (bodyWeight === null || bodyWeight === undefined) return "";
  const result = formatNumber(computeLoad(type, weight, bodyWeight));

  if (type === "bodyweight") {
    return weight === 0
      ? `${formatNumber(bodyWeight)} кг — вес тела`
      : `${formatNumber(bodyWeight)} + ${formatNumber(weight)} = ${result} кг`;
  }

  if (type === "assisted") return `${formatNumber(bodyWeight)} − ${formatNumber(weight)} = ${result} кг`;

  return "";
}
