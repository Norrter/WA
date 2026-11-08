import { useState, type FormEvent } from "react";

import { programs as programsApi } from "../api";
import { useUser } from "../components/Auth";
import { Icon } from "../components/Icon";
import { useScene } from "../components/Scene";
import { useToast } from "../components/Toast";
import { Button, Empty, ErrorNote, Field, Loading, Modal, PageHeader } from "../components/ui";
import { loadProgramDetails } from "../lib/data";
import { orNull, plural } from "../lib/format";
import { navigate } from "../lib/router";
import { useAsync } from "../lib/useAsync";

export function ProgramsPage() {
  useScene("colonnade");

  const me = useUser();
  const { data, error, loading, reload } = useAsync(loadProgramDetails, []);
  const [creating, setCreating] = useState(false);

  if (error) return <ErrorNote error={error} onRetry={reload} />;
  if (loading && !data) return <Loading />;
  if (!data) return null;

  return (
    <div className="page">
      <PageHeader
        title="Программы"
        subtitle={
          me.role === "coach"
            ? "Ваши программы — это и шаблоны для клиентов: назначьте любую из карточки клиента."
            : undefined
        }
        actions={
          <Button variant="primary" icon="plus" onClick={() => setCreating(true)}>
            Новая программа
          </Button>
        }
      />

      {data.length === 0 ? (
        <Empty title="Программ пока нет">
          <p className="muted">
            Программа — это набор тренировочных дней. Создайте свою — или тренер назначит вам
            программу, и она появится здесь.
          </p>
          <Button variant="primary" onClick={() => setCreating(true)}>Создать программу</Button>
        </Empty>
      ) : (
        <ul className="program-list">
          {data.map((program) => {
            const exerciseCount = program.days.reduce((sum, day) => sum + day.exercises.length, 0);

            return (
              <li key={program.id}>
                <a className="program-card" href={`#/programs/${program.id}`}>
                  {program.assigned_by && (
                    <span className="eyebrow program-coach">
                      от тренера {program.assigned_by.username}
                    </span>
                  )}
                  <span className="program-name">{program.name}</span>
                  {program.description && <span className="muted">{program.description}</span>}
                  <span className="program-days">
                    {program.days.length === 0
                      ? "Нет дней"
                      : program.days.map((day) => (
                          <span key={day.id} className="program-day-tag">{day.name}</span>
                        ))}
                  </span>
                  <span className="program-meta">
                    <span>
                      <Icon name="calendar" size={18} />
                      {program.days.length} {plural(program.days.length, "день", "дня", "дней")}
                    </span>
                    <span aria-hidden="true">·</span>
                    <span>
                      <Icon name="dumbbell" size={18} />
                      {exerciseCount} {plural(exerciseCount, "упражнение", "упражнения", "упражнений")}
                    </span>
                  </span>
                </a>
              </li>
            );
          })}
        </ul>
      )}

      {creating && <CreateProgramDialog onClose={() => setCreating(false)} />}
    </div>
  );
}

function CreateProgramDialog({ onClose }: { onClose: () => void }) {
  const toast = useToast();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);

    try {
      const program = await programsApi.create({ name, description: orNull(description) });
      navigate(`/programs/${program.id}`);
    } catch (error) {
      toast.error(error);
      setBusy(false);
    }
  };

  return (
    <Modal title="Новая программа" onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <Field label="Название">
          <input
            autoFocus
            required
            maxLength={150}
            placeholder="Например, Верх / низ"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </Field>
        <Field label="Описание" hint="Необязательно">
          <textarea rows={3} value={description} onChange={(event) => setDescription(event.target.value)} />
        </Field>
        <div className="modal-actions">
          <Button onClick={onClose}>Отмена</Button>
          <Button variant="primary" type="submit" busy={busy}>Создать</Button>
        </div>
      </form>
    </Modal>
  );
}
