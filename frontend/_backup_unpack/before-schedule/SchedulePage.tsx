// Расписание: месяц кружками с отметками, выбранный день
// и тренировки, которые прошли, но не отмечены

import { useState } from "react";

import { workouts } from "../api";
import { useScene } from "../components/Scene";
import { AutoPlanDialog, PlanWorkoutDialog } from "../components/ScheduleDialogs";
import {
  Button,
  displayStatus,
  ErrorNote,
  IconButton,
  Loading,
  PageHeader,
  StatusPill,
} from "../components/ui";
import {
  addDays,
  formatDay,
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
import { workoutNames } from "../lib/workouts";

function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function SchedulePage() {
  useScene("colonnade");

  const now = new Date();
  const todayISO = today();
  const [cursor, setCursor] = useState({ year: now.getFullYear(), month: now.getMonth() });
  const [selected, setSelected] = useState<string | null>(null);
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

  const shiftMonth = (delta: number) => {
    setSelected(null);
    setCursor(({ year, month }) => {
      const date = new Date(year, month + delta, 1);
      return { year: date.getFullYear(), month: date.getMonth() };
    });
  };

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

  // Выбранный день: сегодня, если смотрим текущий месяц, иначе 1-е число
  const selectedDate =
    selected ?? (fromISO(todayISO).getMonth() === cursor.month ? todayISO : firstOfMonth);
  const selectedWorkouts = list.filter((workout) => workout.scheduled_date === selectedDate);
  const unmarked = list.filter(
    (workout) => workout.status === "planned" && workout.scheduled_date < todayISO,
  );

  const dayState = (date: string) => {
    const shown = list
      .filter((workout) => workout.scheduled_date === date)
      .map((workout) => displayStatus(workout.status, workout.scheduled_date));

    if (shown.includes("completed")) return "done";
    if (shown.includes("unmarked")) return "unmarked";
    if (shown.includes("skipped")) return "skipped";
    if (shown.includes("planned")) return "planned";
    return "none";
  };

  const reload = () => {
    setDialog(null);
    void workoutsState.reload();
  };

  return (
    <div className="page schedule-page">
      <PageHeader
        title="Расписание"
        actions={
          <>
            <Button icon="repeat" onClick={() => setDialog({ kind: "auto" })}>
              Автоплан
            </Button>
            <Button variant="primary" icon="plus" onClick={() => setDialog({ kind: "plan" })}>
              Запланировать
            </Button>
          </>
        }
      />

      <section className="calendar-card" aria-label="Календарь тренировок">
        <div className="month-nav">
          <IconButton icon="left" label="Предыдущий месяц" onClick={() => shiftMonth(-1)} />
          <h2 className="month-title">{monthTitle(cursor.year, cursor.month)}</h2>
          <IconButton icon="right" label="Следующий месяц" onClick={() => shiftMonth(1)} />
        </div>

        <div className="month-grid">
          {WEEKDAYS_SHORT.map((name) => (
            <span key={name} className="month-weekday" aria-hidden="true">
              {name}
            </span>
          ))}
          {Array.from({ length: 42 }, (_, index) => {
            const date = addDays(gridStart, index);
            const inMonth = fromISO(date).getMonth() === cursor.month;
            const state = dayState(date);
            const count = list.filter((workout) => workout.scheduled_date === date).length;
            const classes = [
              "month-day",
              inMonth ? "" : "outside",
              date === todayISO ? "is-today" : "",
              date === selectedDate ? "is-selected" : "",
            ].join(" ");

            return (
              <button
                key={date}
                type="button"
                aria-pressed={date === selectedDate}
                aria-label={`${formatDayWithWeekday(date)}${count ? `, тренировок: ${count}` : ""}`}
                className={classes}
                onClick={() => setSelected(date)}
              >
                <span className="month-day-number">{fromISO(date).getDate()}</span>
                <span className={`month-day-dot is-${state}`} aria-hidden="true" />
              </button>
            );
          })}
        </div>

        <div className="legend">
          <span><i className="legend-dot is-done" />выполнена</span>
          <span><i className="legend-dot is-planned" />в плане</span>
          <span><i className="legend-dot is-skipped" />пропуск</span>
          <span><i className="legend-dot is-unmarked" />не отмечена</span>
        </div>
      </section>

      <section className="block day-detail" aria-labelledby="day-title">
        <div className="block-head">
          <h2 className="block-title" id="day-title">
            {selectedDate === todayISO
              ? `Сегодня, ${formatDay(selectedDate)}`
              : capitalize(formatDayWithWeekday(selectedDate))}
          </h2>
          {selectedDate !== todayISO && (
            <button
              type="button"
              className="link-quiet"
              onClick={() => {
                setSelected(todayISO);
                setCursor({ year: now.getFullYear(), month: now.getMonth() });
              }}
            >
              К сегодня
            </button>
          )}
        </div>

        {selectedWorkouts.length === 0 ? (
          <div className="day-empty">
            <span>День отдыха</span>
            <Button small icon="plus" onClick={() => setDialog({ kind: "plan", date: selectedDate })}>
              Запланировать
            </Button>
          </div>
        ) : (
          <div className="day-workouts">
            {selectedWorkouts.map((workout) => {
              const { dayName, programName } = workoutNames(workout, programById);
              const shown = displayStatus(workout.status, workout.scheduled_date);

              return (
                <article key={workout.id} className="day-workout">
                  <div className="day-workout-head">
                    <div>
                      <h3>{dayName}</h3>
                      {programName && <p className="muted small">{programName}</p>}
                    </div>
                    <StatusPill status={workout.status} date={workout.scheduled_date} />
                  </div>
                  <a className="btn btn-secondary btn-block" href={`#/workouts/${workout.id}`}>
                    {shown === "completed"
                      ? "Посмотреть результаты"
                      : shown === "unmarked"
                        ? "Отметить задним числом"
                        : shown === "skipped"
                          ? "Открыть"
                          : "Открыть план"}
                  </a>
                </article>
              );
            })}
          </div>
        )}
      </section>

      {unmarked.length > 0 && (
        <section className="block" aria-labelledby="attention-title">
          <h2 className="section-label is-cold" id="attention-title">Требует внимания</h2>
          <div className="attention-list">
            {unmarked.map((workout) => {
              const { dayName } = workoutNames(workout, programById);

              return (
                <div key={workout.id} className="attention">
                  <div className="attention-text">
                    <strong>
                      {capitalize(formatDayWithWeekday(workout.scheduled_date))} · {dayName}
                    </strong>
                    <span>Тренировка не отмечена</span>
                  </div>
                  <a className="btn btn-cold btn-small" href={`#/workouts/${workout.id}`}>
                    Отметить
                  </a>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {dialog?.kind === "plan" && (
        <PlanWorkoutDialog
          programs={programs}
          date={dialog.date}
          onClose={() => setDialog(null)}
          onDone={reload}
        />
      )}

      {dialog?.kind === "auto" && (
        <AutoPlanDialog programs={programs} onClose={() => setDialog(null)} onDone={reload} />
      )}
    </div>
  );
}
