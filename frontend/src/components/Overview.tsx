// Обзор периода: главные цифры, сравнение с прошлым периодом
// и ключевые упражнения. Используется на экране «Прогресс»
// и в карточке клиента у тренера.

import type { ClientMetrics, KeyExercise, PeriodOverview } from "../api/types";
import { formatDay } from "../lib/dates";
import { formatNumber, formatWeight } from "../lib/format";
import { formatPercent, workoutsDue } from "./Coaching";
import { wellbeingLabel } from "./Feedback";

// «+6%», «−3%», «0%»
export function formatChange(value: number | null): string {
  if (value === null) return "—";

  const percent = Math.round(value * 100);

  if (percent === 0) return "0%";

  return `${percent > 0 ? "+" : "−"}${Math.abs(percent)}%`;
}

function trendClass(value: number | null, higherIsBetter = true): string {
  if (value === null || Math.round(value * 100) === 0) return "";

  return value > 0 === higherIsBetter ? "trend-up" : "trend-down";
}

// Четыре главные цифры периода
export function OverviewFigures({ overview }: { overview: PeriodOverview }) {
  const { current, previous } = overview;

  return (
    <dl className="figures overview-figures">
      <div>
        <dt>Выполнение плана</dt>
        <dd>{formatPercent(current.adherence)}</dd>
        <dd className="figure-note">
          {current.adherence === null
            ? "плана за период не было"
            : `${current.workouts_completed} из ${workoutsDue(current)} тренировок`}
        </dd>
      </div>
      <div>
        <dt>Тренировок</dt>
        <dd>{current.workouts_completed}</dd>
        <dd className="figure-note">было {previous.workouts_completed}</dd>
      </div>
      <div>
        <dt>Новых рекордов</dt>
        <dd>{current.new_records}</dd>
        <dd className="figure-note">лучший результат по упражнению</dd>
      </div>
      <div>
        <dt>Изменение силы</dt>
        <dd className={trendClass(overview.strength_change)}>
          {formatChange(overview.strength_change)}
        </dd>
        <dd className="figure-note">
          {overview.strength_change === null
            ? "нужны тренировки в обоих периодах"
            : "расчётный максимум к прошлому периоду"}
        </dd>
      </div>
    </dl>
  );
}

type Row = {
  label: string;
  value: (metrics: ClientMetrics) => number | null;
  format: (value: number | null) => string;
  higherIsBetter?: boolean;
};

const ROWS: Row[] = [
  {
    label: "Тренировок выполнено",
    value: (m) => m.workouts_completed,
    format: (v) => String(v ?? 0),
  },
  {
    label: "Пропущено и не отмечено",
    value: (m) => m.workouts_skipped + m.workouts_missed,
    format: (v) => String(v ?? 0),
    higherIsBetter: false,
  },
  {
    label: "Выполнение плана",
    value: (m) => m.adherence,
    format: formatPercent,
  },
  {
    label: "Подходов",
    value: (m) => m.total_sets,
    format: (v) => String(v ?? 0),
  },
  {
    label: "Объём, кг",
    value: (m) => m.total_volume,
    format: (v) => formatNumber(v ?? 0),
  },
  {
    label: "Новые рекорды",
    value: (m) => m.new_records,
    format: (v) => String(v ?? 0),
  },
  {
    label: "Самочувствие",
    value: (m) => m.avg_wellbeing,
    format: (v) => (v === null ? "—" : `${formatNumber(v)} · ${wellbeingLabel(v).toLowerCase()}`),
  },
  {
    label: "Сложность",
    value: (m) => m.avg_difficulty,
    format: (v) => (v === null ? "—" : `${formatNumber(v)}/10`),
    // сложность не «лучше» и не «хуже» — без цвета
  },
];

function rowChange(current: number | null, previous: number | null): number | null {
  if (current === null || previous === null || previous === 0) return null;

  return current / previous - 1;
}

// Таблица «прошлый период — этот период — изменение»
export function PeriodComparison({ overview }: { overview: PeriodOverview }) {
  return (
    <table className="comparison">
      <thead>
        <tr>
          <th>Показатель</th>
          <th className="num">
            Прошлый
            <span className="comparison-dates">
              {formatDay(overview.previous_from)} — {formatDay(overview.previous_to)}
            </span>
          </th>
          <th className="num">
            Этот
            <span className="comparison-dates">
              {formatDay(overview.date_from)} — {formatDay(overview.date_to)}
            </span>
          </th>
          <th className="num hide-mobile">Изменение</th>
        </tr>
      </thead>
      <tbody>
        {ROWS.map((row) => {
          const now = row.value(overview.current);
          const before = row.value(overview.previous);
          const change = rowChange(now, before);
          const colored = row.label !== "Сложность";

          return (
            <tr key={row.label}>
              <th scope="row">{row.label}</th>
              <td className="num muted">{row.format(before)}</td>
              <td className="num">{row.format(now)}</td>
              <td
                className={`num hide-mobile ${colored ? trendClass(change, row.higherIsBetter ?? true) : ""}`}
              >
                {formatChange(change)}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

// Ключевые упражнения: лучший расчётный максимум сейчас и раньше
export function KeyExercises({
  items,
  onSelect,
  selectedId,
}: {
  items: KeyExercise[];
  onSelect?: (exerciseId: number) => void;
  selectedId?: number | null;
}) {
  if (items.length === 0) {
    return <p className="muted">За период подходов нет.</p>;
  }

  return (
    <table className="records stack key-exercises">
      <thead>
        <tr>
          <th>Упражнение</th>
          <th>Было</th>
          <th>Стало</th>
          <th>Изменение</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr
            key={item.exercise_id}
            className={`${onSelect ? "selectable" : ""} ${item.exercise_id === selectedId ? "selected" : ""}`}
            onClick={onSelect ? () => onSelect(item.exercise_id) : undefined}
          >
            <td>
              {onSelect ? (
                <button
                  type="button"
                  aria-pressed={item.exercise_id === selectedId}
                  onClick={(event) => {
                    event.stopPropagation();
                    onSelect(item.exercise_id);
                  }}
                >
                  {item.name}
                </button>
              ) : (
                <span className="record-name">{item.name}</span>
              )}
              <span className="athlete-email">
                {item.sets} подх. за период{item.muscle_group ? ` · ${item.muscle_group}` : ""}
              </span>
            </td>
            <td className="num muted" data-label="Было">{formatWeight(item.best_before)}</td>
            <td className="num" data-label="Стало">{formatWeight(item.best_now)}</td>
            <td className={`num ${trendClass(item.change)}`} data-label="Изменение">
              {formatChange(item.change)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
