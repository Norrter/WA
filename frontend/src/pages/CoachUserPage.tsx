// Тренер смотрит одного атлета: сводка, объём по неделям,
// последние тренировки и рекорды. Только чтение.

import { useState } from "react";

import { coach } from "../api";
import { ApiError } from "../api/client";
import { BarChart } from "../components/Charts";
import { useScene } from "../components/Scene";
import { Empty, ErrorNote, Loading, PageHeader, StatusPill } from "../components/ui";
import { formatDay, formatDayWithWeekday, fromISO, today } from "../lib/dates";
import { formatNumber, formatWeight, plural } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { PeriodSwitch, periodStart } from "./CoachPage";

export function CoachUserPage({ id }: { id: number }) {
  useScene("throne");

  const [weeks, setWeeks] = useState(4);
  const now = today();
  const from = periodStart(weeks);

  const profile = useAsync(() => Promise.all([coach.user(id), coach.records(id)]), [id]);
  const period = useAsync(
    () =>
      Promise.all([
        coach.summary(id, from, now),
        coach.weekly(id, Math.max(weeks, 8)),
        coach.workouts(id, from, now),
      ]),
    [id, from, now, weeks],
  );

  const error = profile.error ?? period.error;

  if (error instanceof ApiError && error.status === 404) {
    return (
      <Empty title="Такого атлета нет">
        <a href="#/coach">Ко всем атлетам</a>
      </Empty>
    );
  }

  if (error) {
    return (
      <ErrorNote
        error={error}
        onRetry={() => {
          void profile.reload();
          void period.reload();
        }}
      />
    );
  }

  if (!profile.data || !period.data) return <Loading />;

  const [user, records] = profile.data;
  const [summary, weekly, workouts] = period.data;

  return (
    <div className="page">
      <PageHeader
        back={{ href: "#/coach", label: "Все атлеты" }}
        eyebrow={`Атлет · с нами с ${formatDay(user.created_at.slice(0, 10))}`}
        title={user.username}
        subtitle={user.email}
        actions={<PeriodSwitch weeks={weeks} onChange={setWeeks} />}
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
          <h2 className="block-title">Тренировки за период</h2>
          {workouts.length === 0 ? (
            <Empty title="За этот период тренировок нет">
              <p className="muted">Попробуйте выбрать период длиннее.</p>
            </Empty>
          ) : (
            <ul className="rows">
              {workouts.map((workout) => (
                <li key={workout.id} className="row-item">
                  <span className="row-date">{formatDayWithWeekday(workout.scheduled_date)}</span>
                  <span className="row-main">
                    {workout.day_name}
                    <span className="row-note">{workout.program_name}</span>
                  </span>
                  <span className="row-figures">
                    {workout.sets_completed > 0 &&
                      `${workout.sets_completed} ${plural(workout.sets_completed, "подход", "подхода", "подходов")} · ${formatNumber(workout.volume)} кг`}
                  </span>
                  <StatusPill status={workout.status} />
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section className="block">
        <h2 className="block-title">Рекорды</h2>
        {records.length === 0 ? (
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
              {records.map((record) => (
                <tr key={record.exercise_id}>
                  <td>
                    <span className="record-name">{record.exercise_name}</span>
                    {record.muscle_group && (
                      <span className="athlete-email">{record.muscle_group}</span>
                    )}
                  </td>
                  <td className="num" data-label="Макс. вес">
                    {record.max_weight
                      ? `${formatWeight(record.max_weight.weight)} × ${record.max_weight.reps}`
                      : "—"}
                  </td>
                  <td className="num" data-label="На 1 повтор">{formatWeight(record.best_estimated_1rm)}</td>
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
