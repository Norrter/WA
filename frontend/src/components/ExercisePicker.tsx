// Выбор упражнения из справочника: поиск и фильтр по группе мышц

import { useMemo, useState } from "react";

import type { Exercise } from "../api/types";
import { sortMuscleGroups } from "../lib/muscles";
import { Icon } from "./Icon";

export function MuscleFilter({
  groups,
  value,
  onChange,
}: {
  groups: string[];
  value: string | null;
  onChange: (value: string | null) => void;
}) {
  return (
    <div className="chips" role="group" aria-label="Группа мышц">
      <button
        type="button"
        className={`chip ${value === null ? "active" : ""}`}
        aria-pressed={value === null}
        onClick={() => onChange(null)}
      >
        Все
      </button>
      {groups.map((group) => (
        <button
          key={group}
          type="button"
          className={`chip ${value === group ? "active" : ""}`}
          aria-pressed={value === group}
          onClick={() => onChange(value === group ? null : group)}
        >
          {group}
        </button>
      ))}
    </div>
  );
}

export function filterExercises(
  list: Exercise[],
  search: string,
  muscle: string | null,
): Exercise[] {
  const needle = search.trim().toLowerCase();

  return list.filter(
    (exercise) =>
      (!muscle || exercise.muscle_group === muscle)
      && (!needle || exercise.name.toLowerCase().includes(needle)),
  );
}

export function ExercisePicker({
  exercises,
  onPick,
}: {
  exercises: Exercise[];
  onPick: (exercise: Exercise) => void;
}) {
  const [search, setSearch] = useState("");
  const [muscle, setMuscle] = useState<string | null>(null);

  const groups = useMemo(
    () => sortMuscleGroups(exercises.flatMap((item) => (item.muscle_group ? [item.muscle_group] : []))),
    [exercises],
  );

  const visible = filterExercises(exercises, search, muscle);

  return (
    <div className="picker">
      <div className="search">
        <Icon name="search" size={18} />
        <input
          autoFocus
          placeholder="Найти упражнение"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      </div>
      <MuscleFilter groups={groups} value={muscle} onChange={setMuscle} />
      <ul className="picker-list">
        {visible.map((exercise) => (
          <li key={exercise.id}>
            <button type="button" className="picker-item" onClick={() => onPick(exercise)}>
              <span>{exercise.name}</span>
              <span className="muted">
                {[exercise.muscle_group, exercise.equipment].filter(Boolean).join(", ")}
              </span>
            </button>
          </li>
        ))}
        {visible.length === 0 && <li className="muted picker-empty">Ничего не нашлось</li>}
      </ul>
    </div>
  );
}
