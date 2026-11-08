// Главная: приветствие, сделанное сегодня, неделя кружками,
// ближайшая тренировка с планом и заметки тренера

import { workouts } from "../api";
import type { ProgramDetail, ScheduledWorkout } from "../api/types";
import { useUser } from "../components/Auth";
import { Icon } from "../components/Icon";
import { Meander } from "../components/Meander";
import { SharedNotes } from "../components/MyCoach";
import { useScene } from "../components/Scene";
import { ErrorNote, Loading, displayStatus } from "../components/ui";
import {
  addDays,
  formatDayWithWeekday,
  fromISO,
  relativeDay,
  startOfWeek,
  today,
  weekdayIndex,
  WEEKDAYS_SHORT,
} from "../lib/dates";
import { loadProgramDetails } from "../lib/data";
import { formatReps, formatWeight, plural } from "../lib/format";
import { roman } from "../lib/roman";
import { useAsync } from "../lib/useAsync";
import { workoutNames } from "../lib/workouts";

const WEEKDAYS_FULL = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"];

const MONTHS_GENITIVE = [
  "января", "февраля", "марта", "апреля", "мая", "июня",
  "июля", "августа", "сентября", "октября", "ноября", "декабря",
];

// «СРЕДА · XIV ОКТЯБРЯ»
function solemnDate(value: string): string {
  const date = fromISO(value);
  return `${WEEKDAYS_FULL[weekdayIndex(value)]} · ${roman(date.getDate())} ${MONTHS_GENITIVE[date.getMonth()]}`;
}

export function TodayPage() {
  useScene("olympus");

  const user = useUser();
  const now = today();
  const weekStart = startOfWeek(now);

  const { data, error, loading, reload } = useAsync(
    () =>
      Promise.all([
        workouts.list({ date_from: weekStart, date_to: addDays(now, 60) }),
        loadProgramDetails(),
      ]),
    [now],
  );

  if (error) return <ErrorNote error={error} onRetry={reload} />;
  if (loading && !data) return <Loading />;
  if (!data) return null;

  const [list, programs] = data;
  const programById = new Map(programs.map((program) => [program.id, program]));

  const todays = list.filter((workout) => workout.scheduled_date === now);
  const doneToday = todays.find((workout) => workout.status === "completed");
  const next =
    todays.find((workout) => workout.status === "planned")
    ?? list.find((workout) => workout.status === "planned" && workout.scheduled_date > now);

  const firstName = user.username.trim().split(/\s+/)[0] || user.username;

  return (
    <div className="page today">
      <header className="today-head">
        <p className="eyebrow">{solemnDate(now)}</p>
        <h1 className="page-title">Привет, {firstName}</h1>
      </header>

      {doneToday && <DoneToday workout={doneToday} programs={programById} />}

      <WeekStrip start={weekStart} workouts={list} />

      {next ? (
        <NextWorkout workout={next} programs={programById} />
      ) : (
        <section className="feature-card" aria-labelledby="next-title">
          <Meander />
          <div className="feature-body">
            <p className="eyebrow">Дальше в плане</p>
            <h2 className="feature-title" id="next-title">
              Тренировок пока нет
            </h2>
            <p className="muted">
              Соберите программу и разложите её по календарю — здесь появится ближайшая
              тренировка.
            </p>
            <div className="feature-actions">
              <a className="btn btn-primary" href="#/programs">
                {programs.length === 0 ? "Выбрать программу" : "К программам"}
              </a>
              <a className="btn btn-secondary" href="#/schedule">
                Расписание
              </a>
            </div>
          </div>
        </section>
      )}

      <SharedNotes limit={1} />
    </div>
  );
}

function DoneToday({
  workout,
  programs,
}: {
  workout: ScheduledWorkout;
  programs: Map<number, ProgramDetail>;
}) {
  const { dayName, programName } = workoutNames(workout, programs);

  return (
    <a className="done-today" href={`#/workouts/${workout.id}`}>
      <span className="done-today-check" aria-hidden="true">
        <Icon name="check" size={18} strokeWidth={2.6} />
      </span>
      <span className="done-today-text">
        <strong>Сегодня выполнено</strong>
        <span>
          {dayName}
          {programName && ` · ${programName}`}
        </span>
      </span>
      <Icon name="right" size={18} strokeWidth={2} />
    </a>
  );
}

function NextWorkout({
  workout,
  programs,
}: {
  workout: ScheduledWorkout;
  programs: Map<number, ProgramDetail>;
}) {
  const { day, dayName, programName } = workoutNames(workout, programs);
  const isToday = workout.scheduled_date === today();
  const when = relativeDay(workout.scheduled_date);
  const exercises = day?.exercises ?? [];
  const totalSets = exercises.reduce((sum, item) => sum + item.sets, 0);

  return (
    <section className="feature-card" aria-labelledby="next-title">
      <Meander />
      <div className="feature-body">
        <div className="feature-head">
          <p className="eyebrow">
            {isToday || when === "Завтра"
              ? `${when} · ${formatDayWithWeekday(workout.scheduled_date)}`
              : when}
          </p>
          <h2 className="feature-title" id="next-title">{dayName}</h2>
          <div className="chips">
            {programName && <span className="chip-tag">{programName}</span>}
            {exercises.length > 0 && (
              <span className="chip-tag">
                {exercises.length} {plural(exercises.length, "упражнение", "упражнения", "упражнений")}
              </span>
            )}
            {totalSets > 0 && (
              <span className="chip-tag">
                {totalSets} {plural(totalSets, "подход", "подхода", "подходов")}
              </span>
            )}
          </div>
        </div>

        {exercises.length > 0 && (
          <ol className="plan-list">
            {exercises.map((item, index) => (
              <li key={item.id}>
                <span className="plan-index">{roman(index + 1)}</span>
                <span className="plan-name">{item.exercise.name}</span>
                <span className="plan-target">
                  {item.sets} × {formatReps(item.target_reps, item.target_reps_max)}
                  {item.target_weight !== null && `, ${formatWeight(item.target_weight)}`}
                </span>
              </li>
            ))}
          </ol>
        )}

        <a className="btn btn-primary btn-block btn-start" href={`#/workouts/${workout.id}`}>
          <Icon name="play" size={16} />
          {isToday ? "Начать тренировку" : "Открыть тренировку"}
        </a>
      </div>
    </section>
  );
}

type DayState = "done" | "planned" | "unmarked" | "skipped" | "rest";

function WeekStrip({ start, workouts: list }: { start: string; workouts: ScheduledWorkout[] }) {
  const now = today();
  const days = WEEKDAYS_SHORT.map((weekday, index) => {
    const date = addDays(start, index);
    const dayWorkouts = list.filter((workout) => workout.scheduled_date === date);
    const shown = dayWorkouts.map((workout) => displayStatus(workout.status, workout.scheduled_date));

    const state: DayState = shown.includes("completed")
      ? "done"
      : shown.includes("unmarked")
        ? "unmarked"
        : shown.includes("planned")
          ? "planned"
          : shown.includes("skipped")
            ? "skipped"
            : "rest";

    return { weekday, date, state, workout: dayWorkouts[0] };
  });

  const weekWorkouts = list.filter(
    (workout) => workout.scheduled_date >= start && workout.scheduled_date <= addDays(start, 6),
  );
  const weekDone = weekWorkouts.filter((workout) => workout.status === "completed").length;

  return (
    <section className="block week-block" aria-labelledby="week-title">
      <div className="block-head">
        <h2 className="block-title" id="week-title">Эта неделя</h2>
        {weekWorkouts.length > 0 && (
          <span className="muted small">
            {weekDone} из {weekWorkouts.length} выполнено
          </span>
        )}
      </div>

      <ol className="week-dots">
        {days.map((day) => {
          const label = `${formatDayWithWeekday(day.date)}: ${
            { done: "выполнена", planned: "в плане", unmarked: "не отмечена", skipped: "пропуск", rest: "отдых" }[day.state]
          }`;
          const className = `week-dot is-${day.state} ${day.date === now ? "is-today" : ""}`;
          const number = fromISO(day.date).getDate();

          return (
            <li key={day.date}>
              <span className="week-dot-name">{day.weekday}</span>
              {day.workout ? (
                <a className={className} href={`#/workouts/${day.workout.id}`} aria-label={label}>
                  {number}
                </a>
              ) : (
                <span className={className} aria-label={label}>
                  {number}
                </span>
              )}
            </li>
          );
        })}
      </ol>

      <div className="legend">
        <span><i className="legend-dot is-done" />выполнена</span>
        <span><i className="legend-dot is-planned" />в плане</span>
        <span><i className="legend-dot is-unmarked" />не отмечена</span>
      </div>
    </section>
  );
}
