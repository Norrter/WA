// Прогресс: обзор периода, прогресс по упражнениям, сравнение
// с прошлым периодом, объём, рекорды и история тренировок

import { useState } from "react";

import { stats, workouts as workoutsApi } from "../api";
import { BarChart } from "../components/Charts";
import { PeriodSwitch, periodStart } from "../components/Coaching";
import { ExerciseProgress } from "../components/ExerciseProgress";
import { FeedbackLine } from "../components/Feedback";
import { KeyExercises, OverviewFigures, PeriodComparison } from "../components/Overview";
import { useScene } from "../components/Scene";
import { Empty, ErrorNote, Loading, PageHeader, StatusPill } from "../components/ui";
import { formatDay, formatDayWithWeekday, fromISO, today } from "../lib/dates";
import { formatNumber, formatWeight } from "../lib/format";
import { useAsync } from "../lib/useAsync";

export function ProgressPage() {
  useScene("throne");

  const [weeks, setWeeks] = useState(4);
  const [exerciseId, setExerciseId] = useState<number | null>(null);
  const now = today();
  const from = periodStart(weeks);

  const period = useAsync(
    () =>
      Promise.all([
        stats.overview(from, now),
        stats.weekly(Math.max(weeks, 8)),
        workoutsApi.list({ date_from: from, date_to: now }),
      ]),
    [from, now, weeks],
  );
  const records = useAsync(() => stats.records(), []);

  const error = period.error ?? records.error;

  if (error) {
    return (
      <ErrorNote
        error={error}
        onRetry={() => {
          void period.reload();
          void records.reload();
        }}
      />
    );
  }

  if (!period.data || !records.data) return <Loading />;

  const [overview, weekly, list] = period.data;
  const done = [...list].filter((workout) => workout.status !== "planned").reverse();

  // Упражнение для графика: выбранное, иначе самое частое за период
  const selected =
    exerciseId ?? overview.key_exercises[0]?.exercise_id ?? records.data[0]?.exercise_id ?? null;

  return (
    <div className="page">
      <PageHeader
        title="Прогресс"
        subtitle={`С ${formatDay(from)} по сегодня`}
        actions={<PeriodSwitch weeks={weeks} onChange={setWeeks} />}
      />

      <div className={period.loading ? "is-refreshing" : ""}>
        <section aria-label="Обзор">
          <OverviewFigures overview={overview} />
        </section>

        <section className="block" aria-labelledby="exercise-progress-title">
          <div className="block-head">
            <h2 className="block-title" id="exercise-progress-title">Прогресс по упражнениям</h2>
            {records.data.length > 0 && (
              <select
                aria-label="Упражнение"
                value={selected ?? ""}
                onChange={(event) => setExerciseId(Number(event.target.value))}
              >
                {records.data.map((record) => (
                  <option key={record.exercise_id} value={record.exercise_id}>
                    {record.exercise_name}
                  </option>
                ))}
              </select>
            )}
          </div>
          {selected === null ? (
            <Empty title="Пока нет выполненных подходов">
              <p className="muted">Запишите подходы на экране тренировки — здесь появится график.</p>
            </Empty>
          ) : (
            <ExerciseProgress key={selected} exerciseId={selected} since={from} />
          )}
        </section>

        <section className="block" aria-labelledby="key-title">
          <h2 className="block-title" id="key-title">Ключевые упражнения</h2>
          <p className="muted small">
            Лучший расчётный максимум на 1 повтор за период и за такой же период до него.
          </p>
          <KeyExercises
            items={overview.key_exercises}
            selectedId={selected}
            onSelect={(id) => {
              setExerciseId(id);
              document.getElementById("exercise-progress-title")?.scrollIntoView({ behavior: "smooth" });
            }}
          />
        </section>

        <section className="block" aria-labelledby="compare-title">
          <h2 className="block-title" id="compare-title">Сравнение с прошлым периодом</h2>
          <PeriodComparison overview={overview} />
        </section>

        <section className="block">
          <h2 className="block-title">Объём по неделям, кг</h2>
          <p className="muted small">
            Сумма «вес × повторы» по выполненным подходам. Текущая неделя выделена.
          </p>
          <BarChart
            items={weekly.map((week) => {
              const date = fromISO(week.week_start);
              return {
                label: `${date.getDate()}.${String(date.getMonth() + 1).padStart(2, "0")}`,
                value: week.volume,
                title: `Неделя с ${formatDay(week.week_start)}: ${formatNumber(week.volume)} кг, ${week.sets} подх., ${week.workouts} трен.`,
              };
            })}
          />
        </section>

        <section className="block">
          <div className="block-head">
            <h2 className="block-title">Тренировки за период</h2>
            <a className="link-quiet" href="#/schedule">Календарь</a>
          </div>
          {done.length === 0 ? (
            <p className="muted">За этот период выполненных и пропущенных тренировок нет.</p>
          ) : (
            <ul className="rows">
              {done.map((workout) => (
                <li key={workout.id}>
                  <a className="row-link" href={`#/workouts/${workout.id}`}>
                    <span className="row-date">{formatDayWithWeekday(workout.scheduled_date)}</span>
                    <span className="row-main">
                      {workout.day_name ?? "Тренировка"}
                      <FeedbackLine feedback={workout} />
                    </span>
                    <StatusPill status={workout.status} />
                  </a>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section className="block">
        <h2 className="block-title">Рекорды</h2>
        {records.data.length === 0 ? (
          <Empty title="Рекордов пока нет">
            <p className="muted">Они появятся после первых выполненных подходов.</p>
          </Empty>
        ) : (
          <table className="records stack">
            <thead>
              <tr>
                <th>Упражнение</th>
                <th>Макс. вес</th>
                <th>Максимум на 1 повтор</th>
                <th className="hide-mobile">Последний раз</th>
              </tr>
            </thead>
            <tbody>
              {records.data.map((record) => (
                <tr
                  key={record.exercise_id}
                  className={`selectable ${record.exercise_id === selected ? "selected" : ""}`}
                  onClick={() => setExerciseId(record.exercise_id)}
                >
                  <td>
                    <button
                      type="button"
                      aria-pressed={record.exercise_id === selected}
                      onClick={(event) => {
                        event.stopPropagation();
                        setExerciseId(record.exercise_id);
                        document
                          .getElementById("exercise-progress-title")
                          ?.scrollIntoView({ behavior: "smooth" });
                      }}
                    >
                      {record.exercise_name}
                    </button>
                    {record.muscle_group && (
                      <span className="athlete-email">{record.muscle_group}</span>
                    )}
                  </td>
                  <td className="num" data-label="Макс. вес">
                    {record.max_weight
                      ? `${formatWeight(record.max_weight.weight)} × ${record.max_weight.reps}`
                      : "—"}
                  </td>
                  <td className="num" data-label="На 1 повтор">
                    {formatWeight(record.best_estimated_1rm)}
                  </td>
                  <td className="hide-mobile muted">
                    {record.last_performed ? formatDay(record.last_performed) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
