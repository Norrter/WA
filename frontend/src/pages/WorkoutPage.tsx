import { useEffect, useMemo, useState, type ReactNode } from "react";

import { exercises as exercisesApi, workouts } from "../api";
import type { WorkoutDetail, WorkoutExerciseDetail, WorkoutStatus } from "../api/types";
import { FeedbackDialog, FeedbackLine } from "../components/Feedback";
import { CoachMessage } from "../components/MyCoach";
import { useScene } from "../components/Scene";
import { Icon } from "../components/Icon";
import { PlateBar } from "../components/PlateBar";
import { useToast } from "../components/Toast";
import {
  Button,
  ErrorNote,
  Field,
  IconButton,
  Loading,
  Modal,
  PageHeader,
  Stepper,
  displayStatus,
  statusLabel,
  useConfirm,
} from "../components/ui";
import { formatDayWithWeekday, relativeDay } from "../lib/dates";
import { loadExercises } from "../lib/data";
import { formatDuration, formatNumber, formatReps, formatWeight, plural } from "../lib/format";
import { roman } from "../lib/roman";
import { navigate } from "../lib/router";
import { useAsync } from "../lib/useAsync";

function isDone(item: WorkoutExerciseDetail): boolean {
  return item.performed_sets.length >= item.sets;
}

// Упражнение, которого уже нет в плане, узнаём по самому упражнению
function itemKey(item: WorkoutExerciseDetail): string {
  return item.program_exercise_id !== null
    ? `plan-${item.program_exercise_id}`
    : `done-${item.exercise.id}`;
}

export function WorkoutPage({ id }: { id: number }) {
  useScene("throne");

  const toast = useToast();
  const [confirmDialog, confirm] = useConfirm();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [rating, setRating] = useState(false);
  // key меняется на каждый записанный подход, чтобы таймер начинался заново
  const [rest, setRest] = useState<{ seconds: number; key: number } | null>(null);
  const [moving, setMoving] = useState(false);

  const { data, error, loading, reload, setData } = useAsync(
    () => Promise.all([workouts.full(id), loadExercises()]),
    [id],
  );

  // Оборудование нужно, чтобы показывать блины только для штанги
  const equipmentById = useMemo(
    () => new Map((data?.[1] ?? []).map((exercise) => [exercise.id, exercise.equipment])),
    [data],
  );

  if (error) return <ErrorNote error={error} onRetry={reload} />;
  if (loading && !data) return <Loading />;
  if (!data) return null;

  const [workout] = data;

  const active =
    workout.exercises.find((item) => itemKey(item) === activeId)
    ?? workout.exercises.find((item) => !isDone(item))
    ?? workout.exercises[0];

  const replaceWorkout = (next: WorkoutDetail) => setData([next, data[1]]);

  const refresh = async () => replaceWorkout(await workouts.full(id));

  const setStatus = async (status: WorkoutStatus) => {
    try {
      await workouts.patch(id, { status });
      replaceWorkout({ ...workout, status });

      // Сразу предложить оценить тренировку
      if (status === "completed" && workout.wellbeing === null && workout.difficulty === null) {
        setRating(true);
      }

      toast.success(
        status === "completed"
          ? "Тренировка завершена"
          : status === "skipped"
            ? "Тренировка пропущена"
            : "Тренировка снова в плане",
      );
    } catch (caught) {
      toast.error(caught);
    }
  };

  const remove = async () => {
    if (!(await confirm("Тренировка и все записанные в ней подходы будут удалены.", "Удалить"))) {
      return;
    }

    try {
      await workouts.remove(id);
      toast.success("Тренировка удалена");
      navigate("/");
    } catch (caught) {
      toast.error(caught);
    }
  };

  const totalSets = workout.exercises.reduce((sum, item) => sum + item.sets, 0);
  const doneSets = workout.exercises.reduce(
    (sum, item) => sum + Math.min(item.performed_sets.length, item.sets),
    0,
  );
  const activeIndex = active ? workout.exercises.indexOf(active) : -1;
  const shown = displayStatus(workout.status, workout.scheduled_date);

  return (
    <div className="page page-workout">
      <PageHeader
        eyebrow={
          <span className={`workout-when is-${shown}`}>
            {formatDayWithWeekday(workout.scheduled_date)} · {statusLabel(shown)}
          </span>
        }
        title={workout.program_day_name}
        subtitle={
          <>
            {workout.program_name}
            {workout.coach_name && (
              <span className="muted">программа тренера {workout.coach_name}</span>
            )}
          </>
        }
        actions={
          workout.status !== "completed" && (
            <Button small onClick={() => setStatus("completed")}>
              Завершить
            </Button>
          )
        }
      />

      {totalSets > 0 && (
        <div className="workout-progress" aria-label={`Сделано ${doneSets} из ${totalSets} подходов`}>
          <div className="workout-progress-labels">
            <span>{activeIndex >= 0 ? `Упражнение ${roman(activeIndex + 1)}` : "Подходы"}</span>
            <span>
              {doneSets} из {totalSets} подходов
            </span>
          </div>
          <div className="workout-progress-track">
            <div
              className="workout-progress-fill"
              style={{ width: `${(doneSets / totalSets) * 100}%` }}
            />
          </div>
        </div>
      )}

      {workout.coach_comment && (
        <CoachMessage
          label={`Комментарий тренера${workout.coach_comment_author ? ` · ${workout.coach_comment_author}` : ""}`}
          date={workout.coach_comment_at}
          text={workout.coach_comment}
        />
      )}

      {workout.exercises.length === 0 && (
        <p className="muted">
          В этом дне программы нет упражнений.{" "}
          {workout.program_id !== null && (
            <a href={`#/programs/${workout.program_id}`}>Добавьте их в программу</a>
          )}
        </p>
      )}

      {active && (
        <section className="wx-card" aria-labelledby="active-exercise-title">
          <SetLogger
            key={itemKey(active)}
            workoutId={workout.id}
            workoutDate={workout.scheduled_date}
            item={active}
            index={activeIndex}
            isBarbell={equipmentById.get(active.exercise.id) === "Штанга"}
            onChanged={refresh}
            rest={
              rest && (
                <RestTimer key={rest.key} seconds={rest.seconds} onClose={() => setRest(null)} />
              )
            }
            onLogged={(updated) => {
              if (updated.rest_seconds) {
                setRest({ seconds: updated.rest_seconds, key: Date.now() });
              }

              // Все подходы сделаны — переходим к следующему упражнению
              if (updated.performed_sets.length + 1 >= updated.sets) {
                const nextItem = workout.exercises.find(
                  (other, otherIndex) => otherIndex > activeIndex && !isDone(other),
                );
                if (nextItem) {
                  setActiveId(itemKey(nextItem));
                  setRest(null);
                }
              }
            }}
          />
        </section>
      )}

      {workout.exercises.length > 1 && (
        <section className="block wx-others" aria-labelledby="others-title">
          <h2 className="section-label" id="others-title">Все упражнения</h2>
          <ol className="wx-list">
            {workout.exercises.map((item, index) => {
              const isActive = active !== undefined && itemKey(item) === itemKey(active);
              const done = Math.min(item.performed_sets.length, item.sets);

              return (
                <li key={itemKey(item)}>
                  <button
                    type="button"
                    className={`wx-row ${isActive ? "is-active" : ""} ${isDone(item) ? "is-done" : ""}`}
                    aria-current={isActive ? "step" : undefined}
                    onClick={() => {
                      setActiveId(itemKey(item));
                      window.scrollTo({ top: 0, behavior: "smooth" });
                    }}
                  >
                    <span className="wx-index">{roman(index + 1)}</span>
                    <span className="wx-row-main">
                      <span className="wx-name">{item.exercise.name}</span>
                      <span className="wx-row-note">
                        {done} из {item.sets} {plural(item.sets, "подхода", "подходов", "подходов")}
                      </span>
                    </span>
                    {isDone(item) ? (
                      <span className="wx-row-check" aria-label="Готово">
                        <Icon name="check" size={14} strokeWidth={3} />
                      </span>
                    ) : (
                      <Icon name="right" size={18} strokeWidth={2} />
                    )}
                  </button>
                </li>
              );
            })}
          </ol>
        </section>
      )}

      {workout.status === "completed" && (
        <section className="workout-feedback" aria-label="Оценка тренировки">
          {workout.wellbeing !== null || workout.difficulty !== null || workout.feedback_comment ? (
            <>
              <span className="eyebrow">Ваша оценка</span>
              <FeedbackLine feedback={workout} />
              <Button small variant="ghost" icon="edit" onClick={() => setRating(true)}>
                Изменить
              </Button>
            </>
          ) : (
            <>
              <span className="eyebrow">Оценка</span>
              <span className="muted">Отметьте самочувствие и сложность — так виден прогресс.</span>
              <Button small onClick={() => setRating(true)}>Оценить тренировку</Button>
            </>
          )}
        </section>
      )}

      <div className="workout-footer">
        {workout.status === "completed" ? (
          <Button onClick={() => setStatus("planned")}>Вернуть в план</Button>
        ) : (
          <Button variant="primary" icon="check" onClick={() => setStatus("completed")}>
            Завершить тренировку
          </Button>
        )}
        {workout.status !== "skipped" && (
          <Button onClick={() => setStatus("skipped")}>Пропустить</Button>
        )}
        {workout.status === "skipped" && (
          <Button onClick={() => setStatus("planned")}>Вернуть в план</Button>
        )}
        <Button onClick={() => setMoving(true)}>Перенести</Button>
        <Button variant="danger" onClick={remove}>Удалить</Button>
      </div>

      {moving && (
        <MoveDialog
          workout={workout}
          onClose={() => setMoving(false)}
          onMoved={(date) => {
            replaceWorkout({ ...workout, scheduled_date: date });
            setMoving(false);
            toast.success(`Перенесено на ${relativeDay(date).toLowerCase()}`);
          }}
        />
      )}

      {rating && (
        <FeedbackDialog
          workoutId={workout.id}
          initial={workout}
          onClose={() => setRating(false)}
          onSaved={(feedback) => {
            replaceWorkout({ ...workout, ...feedback });
            setRating(false);
            toast.success("Оценка сохранена");
          }}
        />
      )}

      {confirmDialog}
    </div>
  );
}

// Подходы этого упражнения в прошлой тренировке — для колонки «Прошлый раз»
function usePreviousSets(exerciseId: number, workoutId: number, date: string) {
  const state = useAsync(() => exercisesApi.history(exerciseId, 60), [exerciseId]);

  if (!state.data) return [];

  const earlier = state.data.find(
    (item) => item.scheduled_workout_id !== workoutId && item.date <= date,
  );

  if (!earlier) return [];

  return state.data
    .filter((item) => item.scheduled_workout_id === earlier.scheduled_workout_id)
    .sort((a, b) => a.set_number - b.set_number);
}

function SetLogger({
  workoutId,
  workoutDate,
  item,
  index,
  isBarbell,
  rest,
  onChanged,
  onLogged,
}: {
  workoutId: number;
  workoutDate: string;
  item: WorkoutExerciseDetail;
  index: number;
  isBarbell: boolean;
  rest: ReactNode;
  onChanged: () => Promise<void>;
  onLogged: (item: WorkoutExerciseDetail) => void;
}) {
  const toast = useToast();
  const lastSet = item.performed_sets[item.performed_sets.length - 1];
  const previous = usePreviousSets(item.exercise.id, workoutId, workoutDate);

  const [weight, setWeight] = useState(lastSet?.weight ?? item.target_weight ?? 20);
  const [reps, setReps] = useState(lastSet?.reps ?? item.target_reps ?? 10);
  const [busy, setBusy] = useState(false);

  // Вес с прошлого раза, если в этой тренировке ещё не было подходов
  const [prefilled, setPrefilled] = useState(false);

  useEffect(() => {
    if (prefilled || lastSet || previous.length === 0) return;
    setWeight(previous[0].weight);
    setReps(previous[0].reps);
    setPrefilled(true);
  }, [previous, lastSet, prefilled]);

  const nextNumber = Math.max(0, ...item.performed_sets.map((set) => set.set_number)) + 1;
  const planExerciseId = item.program_exercise_id;
  const canLog = planExerciseId !== null;
  const rowsCount = Math.max(
    item.sets,
    item.performed_sets.length + (canLog ? 1 : 0),
    previous.length,
  );

  const logSet = async () => {
    if (planExerciseId === null) return;
    setBusy(true);

    try {
      await workouts.addSet(workoutId, {
        program_exercise_id: planExerciseId,
        set_number: nextNumber,
        weight,
        reps,
      });
      onLogged(item);
      await onChanged();
    } catch (error) {
      toast.error(error);
    } finally {
      setBusy(false);
    }
  };

  const toggle = async (setId: number, completed: boolean) => {
    try {
      await workouts.patchSet(workoutId, setId, { completed });
      await onChanged();
    } catch (error) {
      toast.error(error);
    }
  };

  const remove = async (setId: number) => {
    try {
      await workouts.removeSet(workoutId, setId);
      await onChanged();
    } catch (error) {
      toast.error(error);
    }
  };

  const value = (w: number, r: number) => `${formatNumber(w)} × ${r}`;

  return (
    <div className="logger">
      <div className="logger-head">
        <span className="wx-card-index">{roman(index + 1)}</span>
        <h2 className="wx-card-title" id="active-exercise-title">{item.exercise.name}</h2>
        {canLog ? (
          <p className="logger-plan">
            План {item.sets} × {formatReps(item.target_reps, item.target_reps_max)}
            {item.target_weight !== null && ` · ${formatWeight(item.target_weight)}`}
            {item.rest_seconds !== null && ` · отдых ${formatDuration(item.rest_seconds)}`}
          </p>
        ) : (
          <p className="logger-plan">
            Этого упражнения больше нет в программе. Сделанные подходы сохранены в истории.
          </p>
        )}
        {item.notes && <p className="logger-notes">{item.notes}</p>}
      </div>

      <table className="sets-table">
        <thead>
          <tr>
            <th scope="col">Подх.</th>
            <th scope="col">Прошлый раз</th>
            <th scope="col">Сегодня</th>
            <th scope="col"><span className="visually-hidden">Отметка</span></th>
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rowsCount }, (_, row) => {
            const set = item.performed_sets[row];
            const before = previous[row];
            const isCurrent = !set && canLog && row === item.performed_sets.length;

            return (
              <tr key={row} className={isCurrent ? "is-current" : set ? (set.completed ? "is-done" : "is-failed") : ""}>
                <th scope="row">{roman(row + 1)}</th>
                <td className="sets-prev">{before ? `${value(before.weight, before.reps)} кг` : "—"}</td>
                <td className="sets-now">
                  {set ? value(set.weight, set.reps) : isCurrent ? value(weight, reps) : "—"}
                </td>
                <td className="sets-actions">
                  {set && (
                    <>
                      <button
                        type="button"
                        className={`set-check ${set.completed ? "on" : ""}`}
                        aria-pressed={set.completed}
                        aria-label={set.completed ? "Отметить как не выполненный" : "Отметить как выполненный"}
                        title={set.completed ? "Выполнен" : "Не выполнен"}
                        onClick={() => toggle(set.id, !set.completed)}
                      >
                        <Icon name={set.completed ? "check" : "close"} size={14} strokeWidth={3} />
                      </button>
                      <IconButton icon="trash" label="Удалить подход" onClick={() => remove(set.id)} />
                    </>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {rest}

      {canLog && (
        <>
          <div className="logger-inputs">
            <Stepper label="Вес, кг" value={weight} step={2.5} onChange={setWeight} />
            <Stepper label="Повторы" value={reps} step={1} min={1} onChange={setReps} />
          </div>

          {isBarbell && <PlateBar weight={weight} />}

          <Button variant="primary" className="btn-block btn-log" onClick={logSet} busy={busy}>
            Записать подход {roman(nextNumber)}
          </Button>
        </>
      )}
    </div>
  );
}

function RestTimer({ seconds, onClose }: { seconds: number; onClose: () => void }) {
  const [endsAt] = useState(() => Date.now() + seconds * 1000);
  const [left, setLeft] = useState(seconds);

  useEffect(() => {
    const timer = setInterval(() => {
      const remaining = Math.max(0, Math.round((endsAt - Date.now()) / 1000));
      setLeft(remaining);

      if (remaining === 0) {
        clearInterval(timer);
        setTimeout(onClose, 4000);
      }
    }, 250);

    return () => clearInterval(timer);
  }, [endsAt, onClose]);

  return (
    <div className={`rest ${left === 0 ? "rest-done" : ""}`} role="timer" aria-live="polite">
      <Icon name="timer" />
      <span className="rest-label">{left === 0 ? "Отдых окончен" : "Отдых"}</span>
      <span className="rest-time">{formatDuration(left)}</span>
      <div
        className="rest-track"
        style={{ width: `${(left / seconds) * 100}%` }}
        aria-hidden="true"
      />
      <Button small variant="ghost" onClick={onClose}>
        {left === 0 ? "Закрыть" : "Пропустить"}
      </Button>
    </div>
  );
}

function MoveDialog({
  workout,
  onClose,
  onMoved,
}: {
  workout: WorkoutDetail;
  onClose: () => void;
  onMoved: (date: string) => void;
}) {
  const toast = useToast();
  const [date, setDate] = useState(workout.scheduled_date);
  const [busy, setBusy] = useState(false);

  return (
    <Modal title="Перенести тренировку" onClose={onClose}>
      <form
        className="form"
        onSubmit={async (event) => {
          event.preventDefault();
          setBusy(true);
          try {
            await workouts.patch(workout.id, { scheduled_date: date });
            onMoved(date);
          } catch (error) {
            toast.error(error);
            setBusy(false);
          }
        }}
      >
        <Field label="Новая дата">
          <input type="date" required value={date} onChange={(event) => setDate(event.target.value)} />
        </Field>
        <div className="modal-actions">
          <Button onClick={onClose}>Отмена</Button>
          <Button variant="primary" type="submit" busy={busy}>Перенести</Button>
        </div>
      </form>
    </Modal>
  );
}
