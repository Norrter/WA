import { useState, type FormEvent } from "react";

import { programs as programsApi } from "../api";
import type { Exercise, ProgramDay, ProgramDetail, ProgramExercise } from "../api/types";
import { useScene } from "../components/Scene";
import { ExercisePicker } from "../components/ExercisePicker";
import { AutoPlanDialog } from "../components/ScheduleDialogs";
import { useToast } from "../components/Toast";
import {
  Button,
  Empty,
  ErrorNote,
  Field,
  IconButton,
  Loading,
  Modal,
  PageHeader,
  useConfirm,
} from "../components/ui";
import { loadExercises } from "../lib/data";
import { formatDuration, formatReps, formatWeight, numberOrNull, orNull } from "../lib/format";
import { navigate } from "../lib/router";
import { useAsync } from "../lib/useAsync";

type Dialog =
  | { kind: "rename" }
  | { kind: "schedule" }
  | { kind: "renameDay"; day: ProgramDay }
  | { kind: "pick"; day: ProgramDay }
  | { kind: "addExercise"; day: ProgramDay; exercise: Exercise }
  | { kind: "editExercise"; day: ProgramDay; item: ProgramExercise };

export function ProgramPage({ id }: { id: number }) {
  useScene("pillars");

  const toast = useToast();
  const [confirmDialog, confirm] = useConfirm();
  const [dialog, setDialog] = useState<Dialog | null>(null);
  const [newDay, setNewDay] = useState("");

  const { data, error, loading, reload, setData } = useAsync(
    () => Promise.all([programsApi.get(id), loadExercises()]),
    [id],
  );

  if (error) return <ErrorNote error={error} onRetry={reload} />;
  if (loading && !data) return <Loading />;
  if (!data) return null;

  const [program, exercises] = data;

  const refresh = async () => setData([await programsApi.get(id), exercises]);

  // Выполнить изменение и перечитать программу
  const act = async (action: () => Promise<unknown>, message?: string) => {
    try {
      await action();
      await refresh();
      if (message) toast.success(message);
    } catch (caught) {
      toast.error(caught);
    }
  };

  const swap = (ids: number[], index: number, direction: number) => {
    const next = [...ids];
    [next[index], next[index + direction]] = [next[index + direction], next[index]];
    return next;
  };

  const addDay = async (event: FormEvent) => {
    event.preventDefault();
    const nextIndex = Math.max(0, ...program.days.map((day) => day.order_index)) + 1;
    await act(() => programsApi.addDay(id, newDay, nextIndex));
    setNewDay("");
  };

  const removeProgram = async () => {
    if (
      !(await confirm(
        "Программа будет удалена вместе с днями, запланированными тренировками и записанными подходами.",
        "Удалить программу",
      ))
    ) {
      return;
    }

    try {
      await programsApi.remove(id);
      toast.success("Программа удалена");
      navigate("/programs");
    } catch (caught) {
      toast.error(caught);
    }
  };

  return (
    <div className="page">
      <PageHeader
        back={{ href: "#/programs", label: "Программы" }}
        title={program.name}
        subtitle={program.description ?? undefined}
        actions={
          <>
            <Button icon="edit" onClick={() => setDialog({ kind: "rename" })}>Изменить</Button>
            <Button
              variant="primary"
              onClick={() => setDialog({ kind: "schedule" })}
              disabled={program.days.length === 0}
            >
              Запланировать
            </Button>
          </>
        }
      />

      {program.days.length === 0 && (
        <Empty title="В программе пока нет дней">
          <p className="muted">Добавьте первый день, например «Верх» или «День A».</p>
        </Empty>
      )}

      <ol className="days">
        {program.days.map((day, dayIndex) => (
          <li key={day.id} className="day">
            <div className="day-head">
              <h2 className="day-name">{day.name}</h2>
              <div className="day-tools">
                <IconButton
                  icon="up"
                  label="Поднять день"
                  disabled={dayIndex === 0}
                  onClick={() =>
                    act(() =>
                      programsApi.reorderDays(id, swap(program.days.map((d) => d.id), dayIndex, -1)),
                    )
                  }
                />
                <IconButton
                  icon="down"
                  label="Опустить день"
                  disabled={dayIndex === program.days.length - 1}
                  onClick={() =>
                    act(() =>
                      programsApi.reorderDays(id, swap(program.days.map((d) => d.id), dayIndex, 1)),
                    )
                  }
                />
                <IconButton
                  icon="edit"
                  label="Переименовать день"
                  onClick={() => setDialog({ kind: "renameDay", day })}
                />
                <IconButton
                  icon="trash"
                  label="Удалить день"
                  onClick={async () => {
                    if (
                      await confirm(
                        `День «${day.name}» и тренировки по нему будут удалены.`,
                        "Удалить день",
                      )
                    ) {
                      await act(() => programsApi.removeDay(id, day.id), "День удалён");
                    }
                  }}
                />
              </div>
            </div>

            {day.exercises.length > 0 && (
              <ol className="day-exercises">
                {day.exercises.map((item, itemIndex) => (
                  <li key={item.id} className="day-exercise">
                    <span className="day-exercise-name">
                      <a href={`#/exercises/${item.exercise.id}`}>{item.exercise.name}</a>
                    </span>
                    <span className="day-exercise-plan">
                      <strong>
                        {item.sets}×{formatReps(item.target_reps, item.target_reps_max)}
                      </strong>
                      {item.target_weight !== null && ` · ${formatWeight(item.target_weight)}`}
                      {item.rest_seconds !== null && ` · отдых ${formatDuration(item.rest_seconds)}`}
                    </span>
                    <span className="day-tools">
                      <IconButton
                        icon="up"
                        label="Выше"
                        disabled={itemIndex === 0}
                        onClick={() =>
                          act(() =>
                            programsApi.reorderExercises(
                              id,
                              day.id,
                              swap(day.exercises.map((e) => e.id), itemIndex, -1),
                            ),
                          )
                        }
                      />
                      <IconButton
                        icon="down"
                        label="Ниже"
                        disabled={itemIndex === day.exercises.length - 1}
                        onClick={() =>
                          act(() =>
                            programsApi.reorderExercises(
                              id,
                              day.id,
                              swap(day.exercises.map((e) => e.id), itemIndex, 1),
                            ),
                          )
                        }
                      />
                      <IconButton
                        icon="edit"
                        label="Изменить план"
                        onClick={() => setDialog({ kind: "editExercise", day, item })}
                      />
                      <IconButton
                        icon="trash"
                        label="Убрать из дня"
                        onClick={async () => {
                          if (
                            await confirm(
                              `«${item.exercise.name}» будет убрано из дня вместе с записанными по нему подходами.`,
                              "Убрать",
                            )
                          ) {
                            await act(() => programsApi.removeExercise(id, day.id, item.id));
                          }
                        }}
                      />
                    </span>
                  </li>
                ))}
              </ol>
            )}

            <Button small icon="plus" onClick={() => setDialog({ kind: "pick", day })}>
              Добавить упражнение
            </Button>
          </li>
        ))}
      </ol>

      <form className="add-day" onSubmit={addDay}>
        <input
          required
          maxLength={150}
          placeholder="Название нового дня"
          aria-label="Название нового дня"
          value={newDay}
          onChange={(event) => setNewDay(event.target.value)}
        />
        <Button type="submit" icon="plus">Добавить день</Button>
      </form>

      <section className="danger-zone">
        <Button variant="danger" icon="trash" onClick={removeProgram}>Удалить программу</Button>
      </section>

      {dialog?.kind === "rename" && (
        <RenameProgramDialog
          program={program}
          onClose={() => setDialog(null)}
          onSaved={(saved) => {
            setData([{ ...program, ...saved }, exercises]);
            setDialog(null);
          }}
        />
      )}

      {dialog?.kind === "schedule" && (
        <AutoPlanDialog
          programs={[program]}
          programId={program.id}
          onClose={() => setDialog(null)}
          onDone={() => setDialog(null)}
        />
      )}

      {dialog?.kind === "renameDay" && (
        <TextDialog
          title="Переименовать день"
          label="Название дня"
          initial={dialog.day.name}
          onClose={() => setDialog(null)}
          onSubmit={async (name) => {
            await act(() => programsApi.renameDay(id, dialog.day.id, name));
            setDialog(null);
          }}
        />
      )}

      {dialog?.kind === "pick" && (
        <Modal title={`Упражнение для дня «${dialog.day.name}»`} onClose={() => setDialog(null)} wide>
          <ExercisePicker
            exercises={exercises}
            onPick={(exercise) => setDialog({ kind: "addExercise", day: dialog.day, exercise })}
          />
        </Modal>
      )}

      {(dialog?.kind === "addExercise" || dialog?.kind === "editExercise") && (
        <PlanDialog
          title={dialog.kind === "addExercise" ? dialog.exercise.name : dialog.item.exercise.name}
          item={dialog.kind === "editExercise" ? dialog.item : undefined}
          onClose={() => setDialog(null)}
          onSubmit={async (values) => {
            if (dialog.kind === "addExercise") {
              const nextIndex =
                Math.max(0, ...dialog.day.exercises.map((item) => item.order_index)) + 1;
              await act(() =>
                programsApi.addExercise(id, dialog.day.id, {
                  ...values,
                  exercise_id: dialog.exercise.id,
                  order_index: nextIndex,
                }),
              );
            } else {
              await act(() =>
                programsApi.patchExercise(id, dialog.day.id, dialog.item.id, values),
              );
            }
            setDialog(null);
          }}
        />
      )}

      {confirmDialog}
    </div>
  );
}

function RenameProgramDialog({
  program,
  onClose,
  onSaved,
}: {
  program: ProgramDetail;
  onClose: () => void;
  onSaved: (saved: { name: string; description: string | null }) => void;
}) {
  const toast = useToast();
  const [name, setName] = useState(program.name);
  const [description, setDescription] = useState(program.description ?? "");
  const [busy, setBusy] = useState(false);

  return (
    <Modal title="Программа" onClose={onClose}>
      <form
        className="form"
        onSubmit={async (event) => {
          event.preventDefault();
          setBusy(true);
          try {
            const saved = await programsApi.patch(program.id, {
              name,
              description: orNull(description),
            });
            onSaved(saved);
          } catch (error) {
            toast.error(error);
            setBusy(false);
          }
        }}
      >
        <Field label="Название">
          <input autoFocus required maxLength={150} value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label="Описание">
          <textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
        </Field>
        <div className="modal-actions">
          <Button onClick={onClose}>Отмена</Button>
          <Button variant="primary" type="submit" busy={busy}>Сохранить</Button>
        </div>
      </form>
    </Modal>
  );
}

function TextDialog({
  title,
  label,
  initial,
  onClose,
  onSubmit,
}: {
  title: string;
  label: string;
  initial: string;
  onClose: () => void;
  onSubmit: (value: string) => Promise<void>;
}) {
  const [value, setValue] = useState(initial);
  const [busy, setBusy] = useState(false);

  return (
    <Modal title={title} onClose={onClose}>
      <form
        className="form"
        onSubmit={async (event) => {
          event.preventDefault();
          setBusy(true);
          await onSubmit(value);
          setBusy(false);
        }}
      >
        <Field label={label}>
          <input autoFocus required maxLength={150} value={value} onChange={(e) => setValue(e.target.value)} />
        </Field>
        <div className="modal-actions">
          <Button onClick={onClose}>Отмена</Button>
          <Button variant="primary" type="submit" busy={busy}>Сохранить</Button>
        </div>
      </form>
    </Modal>
  );
}

interface PlanValues {
  sets: number;
  target_reps: number | null;
  target_reps_max: number | null;
  target_weight: number | null;
  rest_seconds: number | null;
  notes: string | null;
}

// План по упражнению: подходы, повторы, вес, отдых
function PlanDialog({
  title,
  item,
  onClose,
  onSubmit,
}: {
  title: string;
  item?: ProgramExercise;
  onClose: () => void;
  onSubmit: (values: PlanValues) => Promise<void>;
}) {
  const [sets, setSets] = useState(String(item?.sets ?? 3));
  // У нового упражнения подставляем типичные значения, у существующего — его план
  const initial = (value: number | null | undefined, fallback: string) =>
    item ? (value != null ? String(value) : "") : fallback;

  const [reps, setReps] = useState(initial(item?.target_reps, "10"));
  const [repsMax, setRepsMax] = useState(initial(item?.target_reps_max, ""));
  const [weight, setWeight] = useState(initial(item?.target_weight, ""));
  const [rest, setRest] = useState(initial(item?.rest_seconds, "90"));
  const [notes, setNotes] = useState(item?.notes ?? "");
  const [busy, setBusy] = useState(false);

  return (
    <Modal title={title} onClose={onClose}>
      <form
        className="form"
        onSubmit={async (event) => {
          event.preventDefault();
          setBusy(true);
          await onSubmit({
            sets: Number(sets),
            target_reps: numberOrNull(reps),
            target_reps_max: numberOrNull(repsMax),
            target_weight: numberOrNull(weight),
            rest_seconds: numberOrNull(rest),
            notes: orNull(notes),
          });
          setBusy(false);
        }}
      >
        <div className="form-row form-row-3">
          <Field label="Подходы">
            <input type="number" min={1} max={100} required value={sets} onChange={(e) => setSets(e.target.value)} autoFocus />
          </Field>
          <Field label="Повторы">
            <input type="number" min={1} max={1000} value={reps} onChange={(e) => setReps(e.target.value)} />
          </Field>
          <Field label="До" hint="Для диапазона 8–12">
            <input
              type="number"
              min={reps === "" ? 1 : Number(reps)}
              max={1000}
              placeholder="—"
              value={repsMax}
              onChange={(e) => setRepsMax(e.target.value)}
            />
          </Field>
        </div>
        <div className="form-row">
          <Field label="Рабочий вес, кг" hint="Можно оставить пустым">
            <input type="number" min={0} step={0.5} value={weight} onChange={(e) => setWeight(e.target.value)} />
          </Field>
          <Field label="Отдых, секунд">
            <input type="number" min={0} max={3600} step={15} value={rest} onChange={(e) => setRest(e.target.value)} />
          </Field>
        </div>
        <Field label="Заметка">
          <input maxLength={2000} placeholder="Например, пауза внизу" value={notes} onChange={(e) => setNotes(e.target.value)} />
        </Field>
        <div className="modal-actions">
          <Button onClick={onClose}>Отмена</Button>
          <Button variant="primary" type="submit" busy={busy}>
            {item ? "Сохранить" : "Добавить в день"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
