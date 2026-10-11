import { stats, workouts } from "../api";
import type { ProgramDetail, ScheduledWorkout } from "../api/types";
import { Button, ErrorNote, Loading, StatusPill } from "../components/ui";
import { useUser } from "../components/Auth";
import { addDays, fromISO, relativeDay, startOfWeek, today, WEEKDAYS_SHORT } from "../lib/dates";
import { loadProgramDetails } from "../lib/data";
import { formatNumber, formatWeight, plural } from "../lib/format";
import { navigate } from "../lib/router";
import { useAsync } from "../lib/useAsync";

export function TodayPage() {
  const user = useUser();
  const now = today();
  const weekStart = startOfWeek(now);

  const { data, error, loading, reload } = useAsync(
    () =>
      Promise.all([
        workouts.list({ date_from: weekStart, date_to: addDays(now, 60) }),
        loadProgramDetails(),
        stats.summary(addDays(now, -27), now),
      ]),
    [now],
  );

  if (error) return <ErrorNote error={error} onRetry={reload} />;
  if (loading && !data) return <Loading />;
  if (!data) return null;

  const [list, programs, summary] = data;
  const programById = new Map(programs.map((program) => [program.id, program]));

  const todays = list.filter((workout) => workout.scheduled_date === now);
  const next =
    todays.find((workout) => workout.status === "planned")
    ?? list.find((workout) => workout.status === "planned" && workout.scheduled_date >= now);

  return (
    <div className="page">
      <p className="greeting">Привет, {user.username}</p>

      {next ? (
        <NextWorkout workout={next} program={programById.get(next.program_id)} />
      ) : (
        <section className="hero hero-empty">
          <h1 className="hero-title">Тренировок в плане нет</h1>
          <p className="hero-meta">
            Соберите программу и разложите её по календарю, чтобы здесь появилась ближайшая тренировка.
          </p>
          <div className="hero-actions">
            <Button variant="primary" onClick={() => navigate("/programs")}>
              {programs.length === 0 ? "Создать программу" : "К программам"}
            </Button>
            <Button onClick={() => navigate("/schedule")}>Открыть расписание</Button>
          </div>
        </section>
      )}

      <section className="block">
        <h2 className="block-title">Эта неделя</h2>
        <WeekStrip start={weekStart} workouts={list} programs={programById} />
      </section>

      <section className="block">
        <h2 className="block-title">Последние 4 недели</h2>
        <dl className="figures">
          <div>
            <dt>Тренировок выполнено</dt>
            <dd>{summary.workouts_completed}</dd>
          </div>
          <div>
            <dt>Подходов</dt>
            <dd>{summary.total_sets}</dd>
          </div>
          <div>
            <dt>Поднято</dt>
            <dd>{formatNumber(summary.total_volume)} кг</dd>
          </div>
          <div>
            <dt>Пропущено</dt>
            <dd>{summary.workouts_skipped}</dd>
          </div>
        </dl>
      </section>
    </div>
  );
}

function NextWorkout({
  workout,
  program,
}: {
  workout: ScheduledWorkout;
  program?: ProgramDetail;
}) {
  const day = program?.days.find((item) => item.id === workout.program_day_id);
  const isToday = workout.scheduled_date === today();

  return (
    <section className="hero">
      <p className="hero-when">{relativeDay(workout.scheduled_date)}</p>
      <h1 className="hero-title">{day?.name ?? "Тренировка"}</h1>
      <p className="hero-meta">{program?.name}</p>

      {day && day.exercises.length > 0 && (
        <ol className="hero-plan">
          {day.exercises.map((item) => (
            <li key={item.id}>
              <span>{item.exercise.name}</span>
              <span className="hero-plan-target">
                {item.sets}×{item.target_reps ?? "—"}
                {item.target_weight !== null && ` · ${formatWeight(item.target_weight)}`}
              </span>
            </li>
          ))}
        </ol>
      )}

      <div className="hero-actions">
        <Button variant="primary" onClick={() => navigate(`/workouts/${workout.id}`)}>
          {isToday ? "Начать тренировку" : "Открыть тренировку"}
        </Button>
        {day && (
          <span className="muted">
            {day.exercises.length}{" "}
            {plural(day.exercises.length, "упражнение", "упражнения", "упражнений")}
          </span>
        )}
      </div>
    </section>
  );
}

function WeekStrip({
  start,
  workouts: list,
  programs,
}: {
  start: string;
  workouts: ScheduledWorkout[];
  programs: Map<number, ProgramDetail>;
}) {
  const now = today();

  return (
    <ol className="week">
      {WEEKDAYS_SHORT.map((weekday, index) => {
        const date = addDays(start, index);
        const dayWorkouts = list.filter((workout) => workout.scheduled_date === date);

        return (
          <li key={date} className={`week-day ${date === now ? "is-today" : ""}`}>
            <span className="week-name">{weekday}</span>
            <span className="week-number">{fromISO(date).getDate()}</span>
            {dayWorkouts.map((workout) => {
              const day = programs
                .get(workout.program_id)
                ?.days.find((item) => item.id === workout.program_day_id);

              return (
                <a
                  key={workout.id}
                  href={`#/workouts/${workout.id}`}
                  className={`week-workout status-${workout.status}`}
                  title={day?.name}
                >
                  <span className="week-workout-name">{day?.name ?? "Тренировка"}</span>
                  <StatusPill status={workout.status} />
                </a>
              );
            })}
            {dayWorkouts.length === 0 && <span className="week-rest">отдых</span>}
          </li>
        );
      })}
    </ol>
  );
}
