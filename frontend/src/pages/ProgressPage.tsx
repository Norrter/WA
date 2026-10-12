import { useState } from "react";

import { exercises as exercisesApi, stats } from "../api";
import type { ExerciseRecords } from "../api/types";
import { useScene } from "../components/Scene";
import { BarChart } from "../components/Charts";
import { ExerciseProgress } from "../components/ExerciseProgress";
import { Empty, ErrorNote, Loading, PageHeader } from "../components/ui";
import { addDays, formatDay, fromISO, startOfWeek, today } from "../lib/dates";
import { loadProgramDetails } from "../lib/data";
import { formatNumber, formatWeight, plural } from "../lib/format";
import { useAsync } from "../lib/useAsync";

const PERIODS = [4, 12, 26];

interface ExerciseRecordRow {
  id: number;
  name: string;
  records: ExerciseRecords;
}

// Рекорды по всем упражнениям из программ пользователя
async function loadRecords(): Promise<ExerciseRecordRow[]> {
  const programs = await loadProgramDetails();
  const names = new Map<number, string>();

  for (const program of programs) {
    for (const day of program.days) {
      for (const item of day.exercises) names.set(item.exercise.id, item.exercise.name);
    }
  }

  const rows = await Promise.all(
    [...names.entries()].map(async ([id, name]) => ({
      id,
      name,
      records: await exercisesApi.records(id),
    })),
  );

  // Сначала то, что делали недавно; без подходов — в конце
  return rows.sort((a, b) =>
    (b.records.last_performed ?? "").localeCompare(a.records.last_performed ?? "")
    || a.name.localeCompare(b.name, "ru"),
  );
}

export function ProgressPage() {
  useScene("throne");

  const [weeks, setWeeks] = useState(12);
  const [exerciseId, setExerciseId] = useState<number | null>(null);
  const now = today();
  const from = addDays(startOfWeek(now), -(weeks - 1) * 7);

  const period = useAsync(
    () => Promise.all([stats.summary(from, now), stats.weekly(weeks)]),
    [weeks, now],
  );
  const recordsState = useAsync(loadRecords, []);

  const error = period.error ?? recordsState.error;

  if (error) {
    return (
      <ErrorNote
        error={error}
        onRetry={() => {
          void period.reload();
          void recordsState.reload();
        }}
      />
    );
  }

  if (!period.data || !recordsState.data) return <Loading />;

  const [summary, weekly] = period.data;
  const rows = recordsState.data;
  const withData = rows.filter((row) => row.records.total_sets > 0);
  const selected = exerciseId ?? withData[0]?.id ?? rows[0]?.id ?? null;
  const selectedRow = rows.find((row) => row.id === selected);

  return (
    <div className="page">
      <PageHeader
        title="Прогресс"
        actions={
          <div className="segmented" role="group" aria-label="Период">
            {PERIODS.map((value) => (
              <button
                key={value}
                type="button"
                className={weeks === value ? "active" : ""}
                aria-pressed={weeks === value}
                onClick={() => setWeeks(value)}
              >
                {value} {plural(value, "неделя", "недели", "недель")}
              </button>
            ))}
          </div>
        }
      />

      <div className={period.loading ? "is-refreshing" : ""}>
        <dl className="figures">
          <div>
            <dt>Тренировок выполнено</dt>
            <dd>{summary.workouts_completed}</dd>
          </div>
          <div>
            <dt>Пропущено</dt>
            <dd>{summary.workouts_skipped}</dd>
          </div>
          <div>
            <dt>Подходов</dt>
            <dd>{summary.total_sets}</dd>
          </div>
          <div>
            <dt>Поднято</dt>
            <dd>{formatNumber(summary.total_volume)} кг</dd>
          </div>
        </dl>

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
      </div>

      <section className="block">
        <h2 className="block-title">Рекорды</h2>
        {rows.length === 0 ? (
          <Empty title="Добавьте упражнения в программу">
            <p className="muted">Здесь появятся рекорды по упражнениям из ваших программ.</p>
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
              {rows.map((row) => (
                <tr
                  key={row.id}
                  className={`selectable ${row.id === selected ? "selected" : ""}`}
                  onClick={() => setExerciseId(row.id)}
                >
                  <td>
                    <button
                      type="button"
                      aria-pressed={row.id === selected}
                      onClick={() => setExerciseId(row.id)}
                    >
                      {row.name}
                    </button>
                  </td>
                  <td className="num" data-label="Макс. вес">
                    {row.records.max_weight
                      ? `${formatWeight(row.records.max_weight.weight)} × ${row.records.max_weight.reps}`
                      : "—"}
                  </td>
                  <td className="num" data-label="На 1 повтор">{formatWeight(row.records.best_estimated_1rm)}</td>
                  <td className="hide-mobile muted">
                    {row.records.last_performed ? formatDay(row.records.last_performed) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {selectedRow && (
        <section className="block">
          <h2 className="block-title">{selectedRow.name}</h2>
          <ExerciseProgress exerciseId={selectedRow.id} />
        </section>
      )}
    </div>
  );
}
