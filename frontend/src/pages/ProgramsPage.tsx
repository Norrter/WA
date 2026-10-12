import { useState, type FormEvent } from "react";

import { programs as programsApi } from "../api";
import type { ProgramDetail } from "../api/types";
import { useScene } from "../components/Scene";
import { useToast } from "../components/Toast";
import { Button, Empty, ErrorNote, Field, Loading, Modal, PageHeader } from "../components/ui";
import { loadProgramDetails } from "../lib/data";
import { formatDuration, formatReps, orNull, plural } from "../lib/format";
import { navigate } from "../lib/router";
import { useAsync } from "../lib/useAsync";

export function ProgramsPage() {
  useScene("pillars");

  const { data: loaded, error, loading, reload } = useAsync(
    () => Promise.all([loadProgramDetails(), programsApi.templates()]),
    [],
  );
  const [creating, setCreating] = useState(false);
  const [preview, setPreview] = useState<ProgramDetail | null>(null);

  if (error) return <ErrorNote error={error} onRetry={reload} />;
  if (loading && !loaded) return <Loading />;
  if (!loaded) return null;

  const [data, templates] = loaded;

  return (
    <div className="page">
      <PageHeader
        title="Программы"
        actions={
          <Button variant="primary" icon="plus" onClick={() => setCreating(true)}>
            Новая программа
          </Button>
        }
      />

      {data.length === 0 ? (
        <Empty title="Программ пока нет">
          <p className="muted">
            Программа — это набор тренировочных дней. Создайте свою или возьмите готовую ниже.
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
                  <span className="program-name">{program.name}</span>
                  {program.description && <span className="muted">{program.description}</span>}
                  <span className="program-days">
                    {program.days.length === 0
                      ? "Нет дней"
                      : program.days.map((day) => (
                          <span key={day.id} className="program-day-tag">{day.name}</span>
                        ))}
                  </span>
                  <span className="muted">
                    {program.days.length} {plural(program.days.length, "день", "дня", "дней")},{" "}
                    {exerciseCount} {plural(exerciseCount, "упражнение", "упражнения", "упражнений")}
                  </span>
                </a>
              </li>
            );
          })}
        </ul>
      )}

      {templates.length > 0 && (
        <section className="block">
          <h2 className="block-title">Готовые программы</h2>
          <p className="muted small">
            Возьмите себе копию и меняйте её как угодно: дни, упражнения, веса.
          </p>
          <ul className="program-list">
            {templates.map((template) => (
              <li key={template.id}>
                <button
                  type="button"
                  className="program-card program-card-template"
                  onClick={() => setPreview(template)}
                >
                  <span className="program-name">{template.name}</span>
                  {template.description && (
                    <span className="muted">{template.description}</span>
                  )}
                  <span className="program-days">
                    {template.days.map((day) => (
                      <span key={day.id} className="program-day-tag">{day.name}</span>
                    ))}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {creating && <CreateProgramDialog onClose={() => setCreating(false)} />}
      {preview && <TemplateDialog template={preview} onClose={() => setPreview(null)} />}
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

// Просмотр готовой программы и копирование себе
function TemplateDialog({
  template,
  onClose,
}: {
  template: ProgramDetail;
  onClose: () => void;
}) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);

  const take = async () => {
    setBusy(true);

    try {
      const copy = await programsApi.copy(template.id);
      toast.success("Программа добавлена в ваши");
      navigate(`/programs/${copy.id}`);
    } catch (error) {
      toast.error(error);
      setBusy(false);
    }
  };

  return (
    <Modal title={template.name} onClose={onClose} wide>
      {template.description && <p className="modal-text muted">{template.description}</p>}

      <div className="template-days">
        {template.days.map((day) => (
          <section key={day.id} className="template-day">
            <h3 className="template-day-name">{day.name}</h3>
            <ol className="template-exercises">
              {day.exercises.map((item) => (
                <li key={item.id}>
                  <span className="template-exercise-name">
                    {item.exercise.name}
                    {item.notes && <small className="muted">{item.notes}</small>}
                  </span>
                  <span className="template-exercise-plan">
                    {item.sets}×{formatReps(item.target_reps, item.target_reps_max)}
                    {item.rest_seconds !== null && `, отдых ${formatDuration(item.rest_seconds)}`}
                  </span>
                </li>
              ))}
            </ol>
          </section>
        ))}
      </div>

      <div className="modal-actions">
        <Button onClick={onClose}>Закрыть</Button>
        <Button variant="primary" onClick={take} busy={busy}>Взять себе</Button>
      </div>
    </Modal>
  );
}
