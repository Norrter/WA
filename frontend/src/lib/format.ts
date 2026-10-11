const numberFormat = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 });

export function formatNumber(value: number): string {
  return numberFormat.format(value);
}

export function formatWeight(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : `${formatNumber(value)} кг`;
}

// 1 подход, 2 подхода, 5 подходов
export function plural(count: number, one: string, few: string, many: string): string {
  const mod10 = count % 10;
  const mod100 = count % 100;

  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
  return many;
}

export function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const rest = String(seconds % 60).padStart(2, "0");
  return `${minutes}:${rest}`;
}

// Пустая строка из поля ввода -> null
export function orNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

export function numberOrNull(value: string): number | null {
  return value.trim() === "" ? null : Number(value);
}

// Расчётный одноповторный максимум (формула Эпли), как на бэкенде
export function estimate1RM(weight: number, reps: number): number {
  return reps === 1 ? weight : weight * (1 + reps / 30);
}
