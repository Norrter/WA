// Прогресс по одному упражнению: рекорды, график и история подходов.
// Работает и для своих данных, и для клиента тренера (loadHistory).

import { useState } from "react";

import { exercises as exercisesApi } from "../api";
import type { HistoryItem } from "../api/types";
import { formatDay } from "../lib/dates";
import { estimate1RM, formatNumber, formatWeight } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { TrendChart } from "./Charts";
import { Empty, ErrorNote, Loading } from "./ui";

type Metric = "e1rm" | "weight" | "reps";

const METRICS: { value: Metric; label: string; unit: string }[] = [
  { value: "e1rm", label: "Максимум на 1 повтор", unit: "кг" },
  { value: "weight", label: "Рабочий вес", unit: "кг" },
  { value: "reps", label: "Повторы", unit: "повт." },
];

export function ExerciseProgress({
  exerciseId,
  loadHistory = (id) => exercisesApi.history(id, 500),
  since,
}: {
  exerciseId: number;
  loadHistory?: (exerciseId: number) => Promise<HistoryItem[]>;
  // показывать график и историю начиная с этой даты
  since?: string;
}) {
  const [metric, setMetric] = useState<Metric>("e1rm");
  const { data: history, error, loading, reload } = useAsync(
    () => loadHistory(exerciseId),
    [exerciseId],
  );

  if (error) return <ErrorNote error={error} onRetry={reload} />;
  if (loading && !history) return <Loading />;
  if (!history) return null;

  const done = history.filter((item) => item.completed);

  if (done.length === 0) {
    return (
      <Empty title="Пока нет выполненных подходов">
        <p className="muted">После первых записанных подходов здесь появятся рекорды и график.</p>
      </Empty>
    );
  }

  // Рекорды за всё время
  const maxWeight = done.reduce((best, item) =>
    item.weight > best.weight || (item.weight === best.weight && item.reps > best.reps)
      ? item
      : best,
  );
  const best1RM = Math.max(...done.map((item) => estimate1RM(item.weight, item.reps)));
  const volume = done.reduce((sum, item) => sum + item.weight * item.reps, 0);

  // Лучшее значение за каждую дату выбранного периода
  const inPeriod = since ? done.filter((item) => item.date >= since) : done;
  const bestByDate = new Map<string, number>();

  for (const item of inPeriod) {
    const value =
      metric === "e1rm"
        ? estimate1RM(item.weight, item.reps)
        : metric === "weight"
          ? item.weight
          : item.reps;
    bestByDate.set(item.date, Math.max(bestByDate.get(item.date) ?? 0, value));
  }

  const points = [...bestByDate.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, value]) => ({ date, value: Math.round(value * 10) / 10 }));

  // История по тренировкам: дата → подходы
  const sessions = new Map<string, HistoryItem[]>();

  for (const item of since ? history.filter((entry) => entry.date >= since) : history) {
    const key = `${item.date}|${item.scheduled_workout_id}`;
    sessions.set(key, [...(sessions.get(key) ?? []), item]);
  }

  const unit = METRICS.find((item) => item.value === metric)?.unit ?? "";

  return (
    <div className="exercise-progress">
      <dl className="figures">
        <div>
          <dt>Максимальный вес</dt>
          <dd>
            {formatWeight(maxWeight.weight)}
            <small> × {maxWeight.reps}, {formatDay(maxWeight.date)}</small>
          </dd>
        </div>
        <div>
          <dt>Расчётный максимум на 1 повтор</dt>
          <dd>{formatWeight(Math.round(best1RM * 10) / 10)}</dd>
        </div>
        <div>
          <dt>Всего подходов</dt>
          <dd>{done.length}</dd>
        </div>
        <div>
          <dt>Поднято за всё время</dt>
          <dd>{formatNumber(volume)} кг</dd>
        </div>
      </dl>

      <section className="block">
        <div className="block-head">
          <h3 className="block-title">По тренировкам</h3>
          <div className="segmented" role="group" aria-label="Показатель">
            {METRICS.map((item) => (
              <button
                key={item.value}
                type="button"
                className={metric === item.value ? "active" : ""}
                aria-pressed={metric === item.value}
                onClick={() => setMetric(item.value)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
        {points.length > 1 ? (
          <TrendChart points={points} unit={unit} />
        ) : (
          <p className="muted">
            {points.length === 1
              ? "За период одна тренировка — для графика нужно хотя бы две."
              : "За выбранный период подходов нет."}
          </p>
        )}
      </section>

      {sessions.size > 0 && (
        <section className="block">
          <h3 className="block-title">История</h3>
          <ul className="sessions">
            {[...sessions.entries()].slice(0, 15).map(([key, sets]) => (
              <li key={key} className="session">
                <span className="session-date">{formatDay(sets[0].date)}</span>
                <span className="session-sets">
                  {[...sets]
                    .sort((a, b) => a.set_number - b.set_number)
                    .map((set) => (
                      <span key={set.workout_set_id} className={set.completed ? "" : "set-failed"}>
                        {formatNumber(set.weight)}×{set.reps}
                      </span>
                    ))}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
