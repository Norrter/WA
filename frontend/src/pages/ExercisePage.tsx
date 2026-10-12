import { useState } from "react";

import { exercises as exercisesApi } from "../api";
import { useScene } from "../components/Scene";
import { useUser } from "../components/Auth";
import { ExerciseProgress } from "../components/ExerciseProgress";
import { useToast } from "../components/Toast";
import { Button, ErrorNote, Loading, PageHeader, useConfirm } from "../components/ui";
import { navigate } from "../lib/router";
import { useAsync } from "../lib/useAsync";
import { ExerciseDialog } from "./ExercisesPage";

export function ExercisePage({ id }: { id: number }) {
  useScene("struggle");

  const user = useUser();
  const toast = useToast();
  const [confirmDialog, confirm] = useConfirm();
  const [editing, setEditing] = useState(false);
  const { data: exercise, error, loading, reload, setData } = useAsync(
    () => exercisesApi.get(id),
    [id],
  );

  if (error) return <ErrorNote error={error} onRetry={reload} />;
  if (loading && !exercise) return <Loading />;
  if (!exercise) return null;

  const isMine = exercise.created_by_user_id === user.id;

  const remove = async () => {
    if (!(await confirm(`Упражнение «${exercise.name}» будет удалено.`, "Удалить"))) return;

    try {
      await exercisesApi.remove(exercise.id);
      toast.success("Упражнение удалено");
      navigate("/exercises");
    } catch (caught) {
      toast.error(caught);
    }
  };

  return (
    <div className="page">
      <PageHeader
        back={{ href: "#/exercises", label: "Упражнения" }}
        eyebrow={exercise.muscle_group ?? undefined}
        title={exercise.name}
        subtitle={exercise.equipment ?? undefined}
        actions={
          isMine && (
            <>
              <Button icon="edit" onClick={() => setEditing(true)}>Изменить</Button>
              <Button variant="danger" icon="trash" onClick={remove}>Удалить</Button>
            </>
          )
        }
      />

      {exercise.description && <p className="technique">{exercise.description}</p>}
      {!isMine && <p className="muted small">Общее упражнение из справочника, изменить его нельзя.</p>}

      <ExerciseProgress exerciseId={exercise.id} />

      {editing && (
        <ExerciseDialog
          exercise={exercise}
          onClose={() => setEditing(false)}
          onSaved={(saved) => {
            setData(saved);
            setEditing(false);
          }}
        />
      )}

      {confirmDialog}
    </div>
  );
}
