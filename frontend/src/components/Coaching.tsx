// Общие элементы кабинета тренера

import type { ClientFlag, ClientMetrics, FlagReason } from "../api/types";
import { addDays, startOfWeek, today } from "../lib/dates";
import { plural } from "../lib/format";

export const COACH_PERIODS = [4, 12, 26];

const FLAG_LABELS: Record<ClientFlag, string> = {
  on_track: "По плану",
  check: "Проверить",
  progress: "Оценить прогресс",
};

const REASON_LABELS: Record<FlagReason, string> = {
  inactive: "давно не тренировался",
  low_adherence: "низкое выполнение плана",
  stagnation: "давно нет новых рекордов",
};

// Начало периода: понедельник weeks недель назад
export function periodStart(weeks: number): string {
  return addDays(startOfWeek(today()), -(weeks - 1) * 7);
}

export function PeriodSwitch({
  weeks,
  onChange,
}: {
  weeks: number;
  onChange: (weeks: number) => void;
}) {
  return (
    <div className="segmented" role="group" aria-label="Период">
      {COACH_PERIODS.map((value) => (
        <button
          key={value}
          type="button"
          className={weeks === value ? "active" : ""}
          aria-pressed={weeks === value}
          onClick={() => onChange(value)}
        >
          {value} {plural(value, "неделя", "недели", "недель")}
        </button>
      ))}
    </div>
  );
}

export function FlagBadge({ metrics }: { metrics: ClientMetrics }) {
  return (
    <span
      className={`flag flag-${metrics.flag}`}
      title={reasonsText(metrics) || undefined}
    >
      {FLAG_LABELS[metrics.flag]}
    </span>
  );
}

// «давно не тренировался · низкое выполнение плана»
export function reasonsText(metrics: ClientMetrics): string {
  return metrics.reasons.map((reason) => REASON_LABELS[reason]).join(" · ");
}

export function formatPercent(value: number | null): string {
  return value === null ? "—" : `${Math.round(value * 100)}%`;
}

// «сегодня», «вчера», «6 дней назад», «ещё не было»
export function sinceText(days: number | null): string {
  if (days === null) return "ещё не было";
  if (days <= 0) return "сегодня";
  if (days === 1) return "вчера";

  return `${days} ${plural(days, "день", "дня", "дней")} назад`;
}

// Сколько тренировок должно было пройти за период
export function workoutsDue(metrics: ClientMetrics): number {
  return metrics.workouts_completed + metrics.workouts_skipped + metrics.workouts_missed;
}
