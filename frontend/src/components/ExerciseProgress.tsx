// Рекорды, график силы и история подходов по одному упражнению

import { exercises as exercisesApi } from "../api";
import { formatDay } from "../lib/dates";
import { estimate1RM, formatNumber, formatWeight } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { TrendChart } from "./Charts";
import { Empty, ErrorNote, Loading } from "./ui";

export function ExerciseProgress({ exerciseId }: { exerciseId: number }) {
  const { data, error, loading, reload } = useAsync(
    () =>
      Promise.all([
        exercisesApi.records(exerciseId),
        exercisesApi.history(exerciseId),
      ]),
    [exerciseId],
  );

  if (error) return <ErrorNote error={error} onRetry={reload} />;
  if (loading && !data) return <Loading />;
  if (!data) return null;

  const [records, history] = data;

  if (records.total_sets === 0) {
    return (
      <Empty title="Пока нет выполненных подходов">
        <p className="muted">Запишите подходы на экране тренировки, и здесь появятся рекорды и график.</p>
      </Empty>
    );
  }

  // Лучший расчётный максимум за каждую дату
  const bestByDate = new Map<string, number>();

  for (const item of history) {
    if (!item.completed) continue;
    const value = estimate1RM(item.weight, item.reps);
    bestByDate.set(item.date, Math.max(bestByDate.get(item.date) ?? 0, value));
  }

  const points = [...bestByDate.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, value]) => ({ date, value: Math.round(value * 10) / 10 }));

  // История по тренировкам: дата → подходы
  const sessions = new Map<string, typeof history>();

  for (const item of history) {
    const key = `${item.date}|${item.scheduled_workout_id}`;
    sessions.set(key, [...(sessions.get(key) ?? []), item]);
  }

  return (
    <div className="exercise-progress">
      <dl className="figures">
        <div>
          <dt>Максимальный вес</dt>
          <dd>
            {records.max_weight ? formatWeight(records.max_weight.weight) : "—"}
            {records.max_weight && (
              <small> × {records.max_weight.reps}, {formatDay(records.max_weight.date)}</small>
            )}
          </dd>
        </div>
        <div>
          <dt>Расчётный максимум на 1 повтор</dt>
          <dd>{formatWeight(records.best_estimated_1rm)}</dd>
        </div>
        <div>
          <dt>Всего подходов</dt>
          <dd>{records.total_sets}</dd>
        </div>
        <div>
          <dt>Поднято за всё время</dt>
          <dd>{formatNumber(records.total_volume)} кг</dd>
        </div>
      </dl>

      {points.length > 1 && (
        <section className="block">
          <h3 className="block-title">Расчётный максимум по тренировкам</h3>
          <TrendChart points={points} unit="кг" />
        </section>
      )}

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
    </div>
  );
}
