import { useState } from "react";

import { workouts } from "../api";
import type { ProgramDetail, ScheduledWorkout } from "../api/types";
import { useScene } from "../components/Scene";
import { Icon } from "../components/Icon";
import { AutoPlanDialog, PlanWorkoutDialog } from "../components/ScheduleDialogs";
import { Button, Empty, ErrorNote, IconButton, Loading, PageHeader, StatusPill } from "../components/ui";
import {
  addDays,
  formatDayWithWeekday,
  fromISO,
  monthTitle,
  startOfWeek,
  toISO,
  today,
  WEEKDAYS_SHORT,
} from "../lib/dates";
import { loadProgramDetails } from "../lib/data";
import { useAsync } from "../lib/useAsync";

export function SchedulePage() {
  useScene("colonnade");

  const now = new Date();
  const [cursor, setCursor] = useState({ year: now.getFullYear(), month: now.getMonth() });
  const [dialog, setDialog] = useState<
    { kind: "plan"; date?: string } | { kind: "auto" } | null
  >(null);

  // Сетка месяца: 6 недель, начиная с понедельника недели, где 1-е число
  const firstOfMonth = toISO(new Date(cursor.year, cursor.month, 1));
  const gridStart = startOfWeek(firstOfMonth);
  const gridEnd = addDays(gridStart, 41);

  const programsState = useAsync(loadProgramDetails, []);
  const workoutsState = useAsync(
    () => workouts.list({ date_from: gridStart, date_to: gridEnd }),
    [gridStart],
  );

  const shiftMonth = (delta: number) =>
    setCursor(({ year, month }) => {
      const date = new Date(year, month + delta, 1);
      return { year: date.getFullYear(), month: date.getMonth() };
    });

  const error = programsState.error ?? workoutsState.error;

  if (error) {
    return (
      <ErrorNote
        error={error}
        onRetry={() => {
          void programsState.reload();
          void workoutsState.reload();
        }}
      />
    );
  }

  const programs = programsState.data;
  const list = workoutsState.data;

  if (!programs || !list) return <Loading />;

  const programById = new Map(programs.map((program) => [program.id, program]));
  const monthWorkouts = list.filter(
    (workout) => fromISO(workout.scheduled_date).getMonth() === cursor.month,
  );

  return (
    <div className="page page-wide">
      <PageHeader
        title="Расписание"
        actions={
          <>
            <Button onClick={() => setDialog({ kind: "auto" })}>Автоплан</Button>
            <Button variant="primary" icon="plus" onClick={() => setDialog({ kind: "plan" })}>
              Запланировать
            </Button>
          </>
        }
      />

      <div className="month-nav">
        <IconButton icon="left" label="Предыдущий месяц" onClick={() => shiftMonth(-1)} />
        <h2 className="month-title">{monthTitle(cursor.year, cursor.month)}</h2>
        <IconButton icon="right" label="Следующий месяц" onClick={() => shiftMonth(1)} />
        <Button
          small
          variant="ghost"
          onClick={() => setCursor({ year: now.getFullYear(), month: now.getMonth() })}
        >
          Сегодня
        </Button>
      </div>

      <div className="calendar" role="grid" aria-label="Календарь тренировок">
        {WEEKDAYS_SHORT.map((name) => (
          <div key={name} className="calendar-weekday" role="columnheader">
            {name}
          </div>
        ))}
        {Array.from({ length: 42 }, (_, index) => {
          const date = addDays(gridStart, index);
          const inMonth = fromISO(date).getMonth() === cursor.month;
          const dayWorkouts = list.filter((workout) => workout.scheduled_date === date);

          return (
            <div
              key={date}
              role="gridcell"
              className={`calendar-cell ${inMonth ? "" : "outside"} ${date === today() ? "is-today" : ""}`}
            >
              <button
                type="button"
                className="calendar-date"
                aria-label={`Запланировать на ${formatDayWithWeekday(date)}`}
                onClick={() => setDialog({ kind: "plan", date })}
              >
                {fromISO(date).getDate()}
                <Icon name="plus" size={14} />
              </button>
              {dayWorkouts.map((workout) => (
                <CalendarWorkout
                  key={workout.id}
                  workout={workout}
                  program={programById.get(workout.program_id)}
                />
              ))}
            </div>
          );
        })}
      </div>

      <section className="block">
        <h2 className="block-title">Тренировки в этом месяце</h2>
        {monthWorkouts.length === 0 ? (
          <Empty title="В этом месяце тренировок нет">
            <p className="muted">Нажмите на число в календаре или используйте автоплан.</p>
          </Empty>
        ) : (
          <ul className="rows">
            {monthWorkouts.map((workout) => {
              const program = programById.get(workout.program_id);
              const day = program?.days.find((item) => item.id === workout.program_day_id);

              return (
                <li key={workout.id}>
                  <a className="row-link" href={`#/workouts/${workout.id}`}>
                    <span className="row-date">{formatDayWithWeekday(workout.scheduled_date)}</span>
                    <span className="row-main">
                      {day?.name ?? "Тренировка"}
                      <span className="muted"> · {program?.name}</span>
                    </span>
                    <StatusPill status={workout.status} />
                  </a>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {dialog?.kind === "plan" && (
        <PlanWorkoutDialog
          programs={programs}
          date={dialog.date}
          onClose={() => setDialog(null)}
          onDone={() => {
            setDialog(null);
            void workoutsState.reload();
          }}
        />
      )}

      {dialog?.kind === "auto" && (
        <AutoPlanDialog
          programs={programs}
          onClose={() => setDialog(null)}
          onDone={() => {
            setDialog(null);
            void workoutsState.reload();
          }}
        />
      )}
    </div>
  );
}

function CalendarWorkout({
  workout,
  program,
}: {
  workout: ScheduledWorkout;
  program?: ProgramDetail;
}) {
  const day = program?.days.find((item) => item.id === workout.program_day_id);

  return (
    <a
      href={`#/workouts/${workout.id}`}
      className={`calendar-workout status-${workout.status}`}
      title={`${day?.name ?? "Тренировка"} · ${program?.name ?? ""}`}
    >
      {day?.name ?? "Тренировка"}
    </a>
  );
}
