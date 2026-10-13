import { stats, workouts } from "../api";
import type { ProgramDetail, ScheduledWorkout } from "../api/types";
import { useUser } from "../components/Auth";
import { SharedNotes } from "../components/MyCoach";
import { SceneSection, useScene } from "../components/Scene";
import { Button, ErrorNote, Loading, StatusPill } from "../components/ui";
import {
  addDays,
  formatDayWithWeekday,
  fromISO,
  relativeDay,
  startOfWeek,
  today,
  WEEKDAYS_SHORT,
} from "../lib/dates";
import { loadProgramDetails } from "../lib/data";
import { formatNumber, formatReps, formatWeight } from "../lib/format";
import { navigate } from "../lib/router";
import { useAsync } from "../lib/useAsync";
import { workoutNames } from "../lib/workouts";

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
    <div className="today">
      <SceneSection scene="olympus" className="hero" labelledBy="hero-title">
        {next ? (
          <NextWorkout workout={next} programs={programById} />
        ) : (
          <>
            <p className="eyebrow">{user.username}, добро пожаловать</p>
            <h1 id="hero-title" className="hero-title">
              Олимп ждёт
              <br />
              первой тренировки
            </h1>
            <p className="hero-lead">
              Соберите программу и разложите её по календарю — здесь появится
              ближайшая тренировка.
            </p>
            <div className="hero-actions">
              <Button variant="primary" onClick={() => navigate("/programs")}>
                {programs.length === 0 ? "Выбрать программу" : "К программам"}
              </Button>
              <Button variant="ghost" onClick={() => navigate("/schedule")}>
                Расписание
              </Button>
            </div>
          </>
        )}
      </SceneSection>

      <SceneSection scene="colonnade" className="today-rest" labelledBy="week-title">
        <SharedNotes limit={2} />

        <section className="block">
          <h2 id="week-title" className="block-title">Эта неделя</h2>
          <WeekStrip start={weekStart} workouts={list} programs={programById} />
        </section>

        <section className="block">
          <h2 className="block-title">Последние четыре недели</h2>
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
              <dt>Поднято, кг</dt>
              <dd>{formatNumber(summary.total_volume)}</dd>
            </div>
            <div>
              <dt>Пропущено</dt>
              <dd>{summary.workouts_skipped}</dd>
            </div>
          </dl>
        </section>
      </SceneSection>
    </div>
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

  return (
    <>
      <p className="eyebrow">
        {isToday ? `Сегодня, ${formatDayWithWeekday(workout.scheduled_date)}` : when}
      </p>
      <h1 id="hero-title" className="hero-title">{dayName}</h1>
      {programName && <p className="hero-lead">{programName}</p>}

      {day && day.exercises.length > 0 && (
        <ol className="hero-plan">
          {day.exercises.map((item) => (
            <li key={item.id}>
              <span>{item.exercise.name}</span>
              <span className="hero-plan-target">
                {item.sets} × {formatReps(item.target_reps, item.target_reps_max)}
                {item.target_weight !== null && `, ${formatWeight(item.target_weight)}`}
              </span>
            </li>
          ))}
        </ol>
      )}

      <div className="hero-actions">
        <Button variant="primary" onClick={() => navigate(`/workouts/${workout.id}`)}>
          {isToday ? "Начать тренировку" : "Открыть тренировку"}
        </Button>
        <Button variant="ghost" onClick={() => navigate("/schedule")}>
          Расписание
        </Button>
      </div>
    </>
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
              const { dayName } = workoutNames(workout, programs);

              return (
                <a
                  key={workout.id}
                  href={`#/workouts/${workout.id}`}
                  className={`week-workout status-${workout.status}`}
                >
                  <span className="week-workout-name">{dayName}</span>
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
