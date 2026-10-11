import { useEffect, useMemo, useState } from "react";

import { workouts } from "../api";
import type { WorkoutDetail, WorkoutExerciseDetail, WorkoutStatus } from "../api/types";
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
  StatusPill,
  Stepper,
  useConfirm,
} from "../components/ui";
import { relativeDay } from "../lib/dates";
import { loadExercises } from "../lib/data";
import { formatDuration, formatNumber, formatWeight } from "../lib/format";
import { navigate } from "../lib/router";
import { useAsync } from "../lib/useAsync";

function isDone(item: WorkoutExerciseDetail): boolean {
  return item.performed_sets.length >= item.sets;
}

export function WorkoutPage({ id }: { id: number }) {
  const toast = useToast();
  const [confirmDialog, confirm] = useConfirm();
  const [activeId, setActiveId] = useState<number | null>(null);
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
    workout.exercises.find((item) => item.program_exercise_id === activeId)
    ?? workout.exercises.find((item) => !isDone(item))
    ?? workout.exercises[0];

  const replaceWorkout = (next: WorkoutDetail) => setData([next, data[1]]);

  const refresh = async () => replaceWorkout(await workouts.full(id));

  const setStatus = async (status: WorkoutStatus) => {
    try {
      await workouts.patch(id, { status });
      replaceWorkout({ ...workout, status });
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

  return (
    <div className="page page-workout">
      <PageHeader
        back={{ href: "#/", label: "Сегодня" }}
        title={workout.program_day_name}
        subtitle={
          <>
            {workout.program_name}, {relativeDay(workout.scheduled_date).toLowerCase()}{" "}
            <StatusPill status={workout.status} />
          </>
        }
      />

      {totalSets > 0 && (
        <div className="workout-progress" aria-label={`Сделано ${doneSets} из ${totalSets} подходов`}>
          <div className="workout-progress-track">
            <div
              className="workout-progress-fill"
              style={{ width: `${(doneSets / totalSets) * 100}%` }}
            />
          </div>
          <span>
            {doneSets} из {totalSets} подходов
          </span>
        </div>
      )}

      {workout.exercises.length === 0 && (
        <p className="muted">
          В этом дне программы нет упражнений.{" "}
          <a href={`#/programs/${workout.program_id}`}>Добавьте их в программу</a>.
        </p>
      )}

      <ol className="workout-exercises">
        {workout.exercises.map((item, index) => {
          const isActive = item.program_exercise_id === active?.program_exercise_id;

          return (
            <li
              key={item.program_exercise_id}
              className={`wx ${isActive ? "wx-active" : ""} ${isDone(item) ? "wx-done" : ""}`}
            >
              <button
                type="button"
                className="wx-head"
                aria-expanded={isActive}
                onClick={() => setActiveId(item.program_exercise_id)}
              >
                <span className="wx-index">{index + 1}</span>
                <span className="wx-name">{item.exercise.name}</span>
                <span className="wx-count">
                  {item.performed_sets.length}/{item.sets}
                </span>
              </button>

              {isActive && (
                <SetLogger
                  key={item.program_exercise_id}
                  workoutId={workout.id}
                  item={item}
                  isBarbell={equipmentById.get(item.exercise.id) === "Штанга"}
                  onChanged={refresh}
                  onLogged={(updated) => {
                    if (item.rest_seconds) {
                      setRest({ seconds: item.rest_seconds, key: Date.now() });
                    }

                    // Все подходы сделаны — переходим к следующему упражнению
                    if (updated.performed_sets.length + 1 >= updated.sets) {
                      const nextItem = workout.exercises.find(
                        (other, otherIndex) => otherIndex > index && !isDone(other),
                      );
                      if (nextItem) setActiveId(nextItem.program_exercise_id);
                    }
                  }}
                />
              )}
            </li>
          );
        })}
      </ol>

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

      {rest && (
        <RestTimer key={rest.key} seconds={rest.seconds} onClose={() => setRest(null)} />
      )}

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

      {confirmDialog}
    </div>
  );
}

function SetLogger({
  workoutId,
  item,
  isBarbell,
  onChanged,
  onLogged,
}: {
  workoutId: number;
  item: WorkoutExerciseDetail;
  isBarbell: boolean;
  onChanged: () => Promise<void>;
  onLogged: (item: WorkoutExerciseDetail) => void;
}) {
  const toast = useToast();
  const lastSet = item.performed_sets[item.performed_sets.length - 1];

  const [weight, setWeight] = useState(lastSet?.weight ?? item.target_weight ?? 20);
  const [reps, setReps] = useState(lastSet?.reps ?? item.target_reps ?? 10);
  const [busy, setBusy] = useState(false);

  const nextNumber = Math.max(0, ...item.performed_sets.map((set) => set.set_number)) + 1;

  const logSet = async () => {
    setBusy(true);

    try {
      await workouts.addSet(workoutId, {
        program_exercise_id: item.program_exercise_id,
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

  return (
    <div className="logger">
      <p className="logger-plan">
        План: {item.sets} × {item.target_reps ?? "—"}
        {item.target_weight !== null && `, ${formatWeight(item.target_weight)}`}
        {item.rest_seconds !== null && `, отдых ${formatDuration(item.rest_seconds)}`}
      </p>
      {item.notes && <p className="logger-notes">{item.notes}</p>}

      {item.performed_sets.length > 0 && (
        <ol className="sets">
          {item.performed_sets.map((set) => (
            <li key={set.id} className={`set ${set.completed ? "" : "set-failed"}`}>
              <span className="set-number">{set.set_number}</span>
              <span className="set-value">
                {formatNumber(set.weight)} <small>кг</small> × {set.reps}
              </span>
              <button
                type="button"
                className={`set-check ${set.completed ? "on" : ""}`}
                aria-pressed={set.completed}
                aria-label={set.completed ? "Отметить как не выполненный" : "Отметить как выполненный"}
                title={set.completed ? "Выполнен" : "Не выполнен"}
                onClick={() => toggle(set.id, !set.completed)}
              >
                <Icon name={set.completed ? "check" : "close"} size={16} />
              </button>
              <IconButton icon="trash" label="Удалить подход" onClick={() => remove(set.id)} />
            </li>
          ))}
        </ol>
      )}

      <div className="logger-inputs">
        <Stepper label="Вес" unit="кг" value={weight} step={2.5} onChange={setWeight} />
        <Stepper label="Повторы" value={reps} step={1} min={1} onChange={setReps} />
      </div>

      {isBarbell && <PlateBar weight={weight} />}

      <Button variant="primary" className="btn-block btn-log" onClick={logSet} busy={busy}>
        Записать подход {nextNumber}
      </Button>
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
