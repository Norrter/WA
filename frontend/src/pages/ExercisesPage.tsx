import { useMemo, useState, type FormEvent } from "react";

import { exercises as exercisesApi } from "../api";
import type { Exercise, ExerciseInput } from "../api/types";
import { useScene } from "../components/Scene";
import { useUser } from "../components/Auth";
import { filterExercises, MuscleFilter } from "../components/ExercisePicker";
import { Icon } from "../components/Icon";
import { useToast } from "../components/Toast";
import { Button, Empty, ErrorNote, Field, Loading, Modal, PageHeader } from "../components/ui";
import { loadExercises } from "../lib/data";
import { orNull } from "../lib/format";
import { MUSCLE_ORDER, sortMuscleGroups } from "../lib/muscles";
import { navigate } from "../lib/router";
import { useAsync } from "../lib/useAsync";

export const EQUIPMENT = ["Штанга", "Гантели", "Гиря", "Блок", "Тренажёр", "Собственный вес"];

export function ExercisesPage() {
  useScene("struggle");

  const user = useUser();
  const { data, error, loading, reload } = useAsync(loadExercises, []);
  const [search, setSearch] = useState("");
  const [muscle, setMuscle] = useState<string | null>(null);
  const [onlyMine, setOnlyMine] = useState(false);
  const [creating, setCreating] = useState(false);

  const groups = useMemo(
    () => sortMuscleGroups((data ?? []).flatMap((item) => (item.muscle_group ? [item.muscle_group] : []))),
    [data],
  );

  if (error) return <ErrorNote error={error} onRetry={reload} />;
  if (loading && !data) return <Loading />;
  if (!data) return null;

  const visible = filterExercises(data, search, muscle).filter(
    (exercise) => !onlyMine || exercise.created_by_user_id === user.id,
  );

  // Без поиска показываем по группам мышц
  const sections = sortMuscleGroups(visible.map((item) => item.muscle_group ?? "Без группы")).map(
    (group) => ({
      group,
      items: visible.filter((item) => (item.muscle_group ?? "Без группы") === group),
    }),
  );

  return (
    <div className="page">
      <PageHeader
        title="Упражнения"
        subtitle={`${data.length} в справочнике`}
        actions={
          <Button variant="primary" icon="plus" onClick={() => setCreating(true)}>
            Своё упражнение
          </Button>
        }
      />

      <div className="toolbar">
        <div className="search">
          <Icon name="search" size={18} />
          <input
            placeholder="Найти упражнение"
            aria-label="Найти упражнение"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <label className="toggle">
          <input type="checkbox" checked={onlyMine} onChange={(event) => setOnlyMine(event.target.checked)} />
          Только мои
        </label>
      </div>
      <MuscleFilter groups={groups} value={muscle} onChange={setMuscle} />

      {visible.length === 0 ? (
        <Empty title="Ничего не нашлось">
          <p className="muted">Попробуйте другое название или добавьте своё упражнение.</p>
        </Empty>
      ) : (
        sections.map((section) => (
          <section key={section.group} className="block">
            <h2 className="block-title">{section.group}</h2>
            <ul className="rows">
              {section.items.map((exercise) => (
                <li key={exercise.id}>
                  <a className="row-link" href={`#/exercises/${exercise.id}`}>
                    <span className="row-main">{exercise.name}</span>
                    <span className="muted">{exercise.equipment}</span>
                    {exercise.created_by_user_id === user.id && <span className="tag">моё</span>}
                  </a>
                </li>
              ))}
            </ul>
          </section>
        ))
      )}

      {creating && (
        <ExerciseDialog
          onClose={() => setCreating(false)}
          onSaved={(exercise) => navigate(`/exercises/${exercise.id}`)}
        />
      )}
    </div>
  );
}

export function ExerciseDialog({
  exercise,
  onClose,
  onSaved,
}: {
  exercise?: Exercise;
  onClose: () => void;
  onSaved: (exercise: Exercise) => void;
}) {
  const toast = useToast();
  const [name, setName] = useState(exercise?.name ?? "");
  const [muscleGroup, setMuscleGroup] = useState(exercise?.muscle_group ?? "");
  const [equipment, setEquipment] = useState(exercise?.equipment ?? "");
  const [description, setDescription] = useState(exercise?.description ?? "");
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);

    const payload: ExerciseInput = {
      name,
      muscle_group: orNull(muscleGroup),
      equipment: orNull(equipment),
      description: orNull(description),
    };

    try {
      const saved = exercise
        ? await exercisesApi.update(exercise.id, payload)
        : await exercisesApi.create(payload);
      toast.success(exercise ? "Изменения сохранены" : "Упражнение добавлено");
      onSaved(saved);
    } catch (error) {
      toast.error(error);
      setBusy(false);
    }
  };

  return (
    <Modal title={exercise ? "Изменить упражнение" : "Своё упражнение"} onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <Field label="Название">
          <input autoFocus required maxLength={150} value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <div className="form-row">
          <Field label="Группа мышц">
            <input list="muscle-groups" maxLength={100} value={muscleGroup} onChange={(e) => setMuscleGroup(e.target.value)} />
            <datalist id="muscle-groups">
              {MUSCLE_ORDER.map((group) => <option key={group} value={group} />)}
            </datalist>
          </Field>
          <Field label="Оборудование">
            <input list="equipment" maxLength={100} value={equipment} onChange={(e) => setEquipment(e.target.value)} />
            <datalist id="equipment">
              {EQUIPMENT.map((item) => <option key={item} value={item} />)}
            </datalist>
          </Field>
        </div>
        <Field label="Подсказка по технике">
          <textarea rows={3} maxLength={5000} value={description} onChange={(e) => setDescription(e.target.value)} />
        </Field>
        <div className="modal-actions">
          <Button onClick={onClose}>Отмена</Button>
          <Button variant="primary" type="submit" busy={busy}>
            {exercise ? "Сохранить" : "Добавить"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
