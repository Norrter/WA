// Питание: подписи, расчёт нормы (как на бэкенде) и мелкие помощники

import type { Activity, Anthropometry, Goal, Macros, Meal } from "../api/types";

export const MEALS: { value: Meal; label: string }[] = [
  { value: "breakfast", label: "Завтрак" },
  { value: "lunch", label: "Обед" },
  { value: "dinner", label: "Ужин" },
  { value: "snack", label: "Перекусы" },
];

export const ACTIVITIES: { value: Activity; label: string; hint: string; factor: number }[] = [
  { value: "minimal", label: "Минимальная", hint: "сидячая работа, без тренировок", factor: 1.2 },
  { value: "light", label: "Низкая", hint: "1–3 тренировки в неделю", factor: 1.375 },
  { value: "moderate", label: "Средняя", hint: "3–5 тренировок в неделю", factor: 1.55 },
  { value: "high", label: "Высокая", hint: "6–7 тренировок в неделю", factor: 1.725 },
  { value: "extreme", label: "Очень высокая", hint: "физический труд или 2 тренировки в день", factor: 1.9 },
];

export const GOALS: { value: Goal; label: string; hint: string }[] = [
  { value: "lose", label: "Похудение", hint: "−15 % калорий, белок 2 г/кг" },
  { value: "maintain", label: "Поддержание", hint: "калории = расход, белок 1,6 г/кг" },
  { value: "gain", label: "Набор массы", hint: "+10 % калорий, белок 1,8 г/кг" },
];

const GOAL_FACTOR: Record<Goal, number> = { lose: 0.85, maintain: 1, gain: 1.1 };
const PROTEIN_PER_KG: Record<Goal, number> = { lose: 2, maintain: 1.6, gain: 1.8 };
const FAT_PER_KG: Record<Goal, number> = { lose: 0.9, maintain: 1, gain: 1 };

// Миффлин — Сан Жеор → активность → цель → белок и жиры на кг, углеводы — остаток
export function calculateNorm(data: Anthropometry, weight: number): Macros & { bmr: number; tdee: number } {
  const bmr = 10 * weight + 6.25 * data.height_cm - 5 * data.age + (data.sex === "male" ? 5 : -161);
  const factor = ACTIVITIES.find((item) => item.value === data.activity)?.factor ?? 1.2;
  const tdee = bmr * factor;
  const kcal = Math.round((tdee * GOAL_FACTOR[data.goal]) / 10) * 10;
  const protein = Math.round(PROTEIN_PER_KG[data.goal] * weight);
  const fat = Math.round(FAT_PER_KG[data.goal] * weight);
  const carbs = Math.max(0, Math.round((kcal - protein * 4 - fat * 9) / 4));

  return { bmr: Math.round(bmr), tdee: Math.round(tdee), kcal, protein, fat, carbs };
}

// Приём пищи по времени суток
export function mealByTime(date = new Date()): Meal {
  const hour = date.getHours();
  if (hour < 11) return "breakfast";
  if (hour < 16) return "lunch";
  if (hour < 21) return "dinner";
  return "snack";
}

// «12,5» → 12.5; пусто или мусор → null
export function parseAmount(text: string): number | null {
  const trimmed = text.trim().replace(",", ".");
  if (trimmed === "") return null;
  const value = Number(trimmed);
  return Number.isFinite(value) && value >= 0 ? value : null;
}

export function amountText(value: number | null | undefined): string {
  return value === null || value === undefined ? "" : String(value).replace(".", ",");
}

export function round1(value: number): number {
  return Math.round(value * 10) / 10;
}

export function scaleMacros(macros: Macros, factor: number): Macros {
  return {
    kcal: round1(macros.kcal * factor),
    protein: round1(macros.protein * factor),
    fat: round1(macros.fat * factor),
    carbs: round1(macros.carbs * factor),
  };
}
