// Карточка клиента для тренера: статус, главные показатели, заметки,
// программы и расписание, тренировки с оценками, прогресс по
// упражнениям, сравнение периодов и рекорды. Данные клиента тренер
// только смотрит; менять может назначенные им программы.

import { useState, type FormEvent } from "react";

import { coach, programs as programsApi } from "../api";
import { ApiError } from "../api/client";
import type { CoachNote, Program, ProgramDetail } from "../api/types";
import { BarChart } from "../components/Charts";
import {
  FlagBadge,
  PeriodSwitch,
  periodStart,
  reasonsText,
  sinceText,
  workoutsDue,
} from "../components/Coaching";
import { ExerciseProgress } from "../components/ExerciseProgress";
import { FeedbackLine, wellbeingLabel } from "../components/Feedback";
import { formatChange, KeyExercises, PeriodComparison } from "../components/Overview";
import { useScene } from "../components/Scene";
import { useToast } from "../components/Toast";
import {
  Button,
  Empty,
  ErrorNote,
  Field,
  IconButton,
  Loading,
  Modal,
  StatusPill,
  useConfirm,
} from "../components/ui";
import {
  addDays,
  formatDay,
  formatDayWithWeekday,
  fromISO,
  relativeDay,
  today,
  WEEKDAYS_SHORT,
} from "../lib/dates";
import { formatNumber, formatWeight, plural } from "../lib/format";
import { navigate } from "../lib/router";
import { useAsync } from "../lib/useAsync";

// Плавно прокрутить к разделу; focus — сразу поставить курсор в поле
function scrollToId(elementId: string, focus = false) {
  const element = document.getElementById(elementId);
  element?.scrollIntoView({ behavior: "smooth", block: "center" });
  if (focus && element instanceof HTMLElement) element.focus({ preventScroll: true });
}

export function CoachUserPage({ id }: { id: number }) {
  useScene("throne");

  const toast = useToast();
  const [confirmDialog, confirm] = useConfirm();
  const [weeks, setWeeks] = useState(4);
  const [exerciseId, setExerciseId] = useState<number | null>(null);
  const [assigning, setAssigning] = useState(false);
  const now = today();
  const from = periodStart(weeks);

  const records = useAsync(() => coach.records(id), [id]);
  const plan = useAsync(
    () =>
      Promise.all([
        coach.programs(id),
        coach.workouts(id, { date_from: now, date_to: addDays(now, 27), order: "asc", limit: 10 }),
      ]),
    [id, now],
  );
  const period = useAsync(
    () =>
      Promise.all([
        coach.card(id, from, now),
        coach.overview(id, from, now),
        coach.weekly(id, Math.max(weeks, 8)),
        coach.workouts(id, { date_from: from, date_to: now }),
      ]),
    [id, from, now, weeks],
  );

  const error = period.error ?? records.error ?? plan.error;

  if (error instanceof ApiError && error.status === 404) {
    return (
      <Empty title="Клиент недоступен">
        <p className="muted">Сотрудничество завершено или клиента нет.</p>
        <a href="#/coach">Ко всем клиентам</a>
      </Empty>
    );
  }

  if (error) {
    return (
      <ErrorNote
        error={error}
        onRetry={() => {
          void records.reload();
          void period.reload();
          void plan.reload();
        }}
      />
    );
  }

  if (!period.data || !records.data || !plan.data) return <Loading />;

  const [card, overview, weekly, workouts] = period.data;
  const [clientPrograms, upcoming] = plan.data;
  const { client, link, metrics } = card;
  const due = workoutsDue(metrics);
  const reasons = reasonsText(metrics);
  const selected =
    exerciseId ?? overview.key_exercises[0]?.exercise_id ?? records.data[0]?.exercise_id ?? null;
  // Прошедшие тренировки, которые клиент так и не отметил
  const unmarked = workouts.filter(
    (workout) => workout.status === "planned" && workout.scheduled_date < now,
  );

  const endCooperation = async () => {
    const agreed = await confirm(
      `${client.username} перестанет быть вашим клиентом, и вы больше не увидите его тренировки. История тренировок и назначенные программы останутся у клиента, а ваши заметки сохранятся, если вы снова начнёте работать вместе.`,
      "Завершить",
    );

    if (!agreed) return;

    try {
      await coach.end(id);
      toast.success("Сотрудничество завершено");
      navigate("/coach");
    } catch (caught) {
      toast.error(caught);
    }
  };

  return (
    <div className="page">
      <header className="client-hero">
        <span className="avatar avatar-xl" aria-hidden="true">
          {client.username.trim().charAt(0).toUpperCase()}
        </span>
        <div className="client-hero-text">
          <h1 className="page-title">{client.username}</h1>
          <p className="muted small">
            {client.email}
            {link.responded_at && ` · клиент с ${formatDay(link.responded_at.slice(0, 10))}`}
          </p>
        </div>
      </header>

      <div className="client-actions">
        <Button variant="primary" onClick={() => scrollToId("new-note", true)}>
          Заметка
        </Button>
        <Button onClick={() => setAssigning(true)}>Программа</Button>
        <Button onClick={() => scrollToId("upcoming-title")}>Расписание</Button>
      </div>

      <div className={`client-status flag-row-${metrics.flag}`}>
        <FlagBadge metrics={metrics} />
        <span className="client-status-text">
          {reasons
            ? `${reasons.charAt(0).toUpperCase()}${reasons.slice(1)}`
            : metrics.flag === "on_track"
              ? "Тренируется по плану, рекорды растут"
              : ""}
        </span>
      </div>

      {unmarked.length > 0 && (
        <div className="attention">
          <div className="attention-text">
            <strong>
              {unmarked.length}{" "}
              {plural(unmarked.length, "тренировка не отмечена", "тренировки не отмечены", "тренировок не отмечено")}
            </strong>
            <span>
              {formatDayWithWeekday(unmarked[0].scheduled_date)} · {unmarked[0].day_name}
            </span>
          </div>
          <a className="btn btn-cold btn-small" href={`#/coach/clients/${id}/workouts/${unmarked[0].id}`}>
            Открыть
          </a>
        </div>
      )}

      <div className={period.loading ? "is-refreshing" : ""}>
        <div className="block-head summary-head">
          <h2 className="block-title">Сводка</h2>
          <PeriodSwitch weeks={weeks} onChange={setWeeks} />
        </div>
        <dl className="figures figures-card">
          <div>
            <dt>Выполнено / запланировано</dt>
            <dd>
              {metrics.workouts_completed}
              <small> / {due}</small>
            </dd>
            <dd className="figure-note">
              {metrics.adherence === null
                ? "плана за период не было"
                : `${Math.round(metrics.adherence * 100)}% плана`}
            </dd>
          </div>
          <div>
            <dt>Последняя тренировка</dt>
            <dd className="figure-text">{sinceText(metrics.days_since_last_workout)}</dd>
            {metrics.last_workout && (
              <dd className="figure-note">{formatDay(metrics.last_workout)}</dd>
            )}
          </div>
          <div>
            <dt>Пропуски</dt>
            <dd>{metrics.workouts_skipped + metrics.workouts_missed}</dd>
            {metrics.workouts_missed > 0 && (
              <dd className="figure-note">
                {metrics.workouts_missed} не{" "}
                {plural(metrics.workouts_missed, "отмечена", "отмечены", "отмечены")}
              </dd>
            )}
          </div>
          <div>
            <dt>Следующее занятие</dt>
            {metrics.next_workout ? (
              <>
                <dd className="figure-text">{relativeDay(metrics.next_workout.date)}</dd>
                <dd className="figure-note">{metrics.next_workout.day_name}</dd>
              </>
            ) : (
              <dd className="figure-text">не запланировано</dd>
            )}
          </div>
          <div>
            <dt>Изменение силы</dt>
            <dd className={trendOf(overview.strength_change)}>
              {formatChange(overview.strength_change)}
            </dd>
            <dd className="figure-note">
              {metrics.new_records} {plural(metrics.new_records, "рекорд", "рекорда", "рекордов")} за период
            </dd>
          </div>
          <div>
            <dt>Самочувствие · сложность</dt>
            <dd className="figure-text">
              {metrics.avg_wellbeing !== null
                ? wellbeingLabel(metrics.avg_wellbeing).toLowerCase()
                : "—"}
            </dd>
            <dd className="figure-note">
              {metrics.avg_difficulty !== null
                ? `сложность в среднем ${formatNumber(metrics.avg_difficulty)}/10`
                : "клиент ещё не оценивал тренировки"}
            </dd>
          </div>
        </dl>

        <Notes clientId={id} />

        <section className="block" aria-labelledby="client-programs-title">
          <div className="block-head">
            <h2 className="block-title" id="client-programs-title">Программы</h2>
            <Button small variant="primary" icon="plus" onClick={() => setAssigning(true)}>
              Назначить
            </Button>
          </div>
          {clientPrograms.length === 0 ? (
            <p className="muted">
              У клиента нет программ. Назначьте свою программу или готовый шаблон — у клиента
              появится копия, которую ведёте вы.
            </p>
          ) : (
            <ul className="rows">
              {clientPrograms.map((program) => (
                <li key={program.id}>
                  <a className="row-link" href={`#/programs/${program.id}`}>
                    <span className="row-main">
                      {program.name}
                      <span className="row-note">
                        {program.can_edit
                          ? "назначена вами — можно менять"
                          : program.assigned_by
                            ? `от тренера ${program.assigned_by.username}`
                            : "составил клиент — только просмотр"}
                      </span>
                    </span>
                    {program.can_edit && <span className="tag">ваша</span>}
                  </a>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="block" aria-labelledby="upcoming-title">
          <h2 className="block-title" id="upcoming-title">Расписание на 4 недели</h2>
          {upcoming.length === 0 ? (
            <p className="muted">
              Ближайших тренировок нет. Разложите программу по календарю: откройте её и нажмите
              «Запланировать».
            </p>
          ) : (
            <ul className="rows">
              {upcoming.map((workout) => (
                <li key={workout.id}>
                  <a className="row-link row-item" href={`#/coach/clients/${id}/workouts/${workout.id}`}>
                    <span className="row-date">{relativeDay(workout.scheduled_date)}</span>
                    <span className="row-main">
                      {workout.day_name}
                      <span className="row-note">{workout.program_name}</span>
                    </span>
                    <StatusPill status={workout.status} date={workout.scheduled_date} />
                  </a>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="block">
          <h2 className="block-title">Тренировки за период</h2>
          {workouts.length === 0 ? (
            <Empty title="За этот период тренировок нет">
              <p className="muted">Попробуйте выбрать период длиннее.</p>
            </Empty>
          ) : (
            <ul className="rows">
              {workouts.map((workout) => (
                <li key={workout.id}>
                  <a className="row-link row-item" href={`#/coach/clients/${id}/workouts/${workout.id}`}>
                    <span className="row-date">{formatDayWithWeekday(workout.scheduled_date)}</span>
                    <span className="row-main">
                      {workout.day_name}
                      <span className="row-note">{workout.program_name}</span>
                      <FeedbackLine feedback={workout} />
                      {workout.coach_comment && (
                        <span className="row-coach-comment">Ваш комментарий: {workout.coach_comment}</span>
                      )}
                    </span>
                    <span className="row-figures">
                      {workout.sets_completed > 0 &&
                        `${workout.sets_completed} ${plural(workout.sets_completed, "подход", "подхода", "подходов")} · ${formatNumber(workout.volume)} кг`}
                    </span>
                    <StatusPill status={workout.status} date={workout.scheduled_date} />
                  </a>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="block" aria-labelledby="client-exercise-title">
          <div className="block-head">
            <h2 className="block-title" id="client-exercise-title">Прогресс по упражнениям</h2>
            {records.data.length > 0 && (
              <select
                aria-label="Упражнение"
                value={selected ?? ""}
                onChange={(event) => setExerciseId(Number(event.target.value))}
              >
                {records.data.map((record) => (
                  <option key={record.exercise_id} value={record.exercise_id}>
                    {record.exercise_name}
                  </option>
                ))}
              </select>
            )}
          </div>
          <KeyExercises
            items={overview.key_exercises}
            selectedId={selected}
            onSelect={setExerciseId}
          />
          {selected !== null && (
            <ExerciseProgress
              key={selected}
              exerciseId={selected}
              since={from}
              loadHistory={(exercise) => coach.exerciseHistory(id, exercise, 500)}
            />
          )}
        </section>

        <section className="block">
          <h2 className="block-title">Сравнение с прошлым периодом</h2>
          <PeriodComparison overview={overview} />
        </section>

        <section className="block">
          <h2 className="block-title">Объём по неделям, кг</h2>
          <BarChart
            items={weekly.map((week) => {
              const date = fromISO(week.week_start);
              return {
                label: `${date.getDate()}.${String(date.getMonth() + 1).padStart(2, "0")}`,
                value: week.volume,
                title: `Неделя с ${formatDay(week.week_start)}: ${formatNumber(week.volume)} кг, ${week.sets} подх., ${week.workouts} трен.`,
              };
            })}
          />
        </section>
      </div>

      <section className="block">
        <h2 className="block-title">История рекордов</h2>
        {records.data.length === 0 ? (
          <Empty title="Рекордов пока нет">
            <p className="muted">Они появятся после первых выполненных подходов.</p>
          </Empty>
        ) : (
          <table className="records stack">
            <thead>
              <tr>
                <th>Упражнение</th>
                <th>Макс. вес</th>
                <th>Максимум на 1 повтор</th>
                <th className="hide-mobile">Последний раз</th>
              </tr>
            </thead>
            <tbody>
              {records.data.map((record) => (
                <tr key={record.exercise_id}>
                  <td>
                    <span className="record-name">{record.exercise_name}</span>
                    {record.muscle_group && (
                      <span className="athlete-email">{record.muscle_group}</span>
                    )}
                  </td>
                  <td className="num" data-label="Макс. вес">
                    {record.max_weight
                      ? `${formatWeight(record.max_weight.weight)} × ${record.max_weight.reps}`
                      : "—"}
                  </td>
                  <td className="num" data-label="На 1 повтор">
                    {formatWeight(record.best_estimated_1rm)}
                  </td>
                  <td className="hide-mobile muted">
                    {record.last_performed ? formatDay(record.last_performed) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="danger-zone">
        <h2 className="block-title">Сотрудничество</h2>
        <p className="muted">
          История тренировок и программы останутся у клиента. Вы перестанете видеть его данные.
        </p>
        <Button variant="danger" onClick={() => void endCooperation()}>
          Завершить сотрудничество
        </Button>
      </section>

      {assigning && (
        <AssignProgramDialog
          clientId={id}
          clientName={client.username}
          onClose={() => setAssigning(false)}
          onDone={(programId) => {
            setAssigning(false);
            void plan.reload();
            void period.reload();
            navigate(`/programs/${programId}`);
          }}
        />
      )}

      {confirmDialog}
    </div>
  );
}

function trendOf(value: number | null): string {
  if (value === null || Math.round(value * 100) === 0) return "";
  return value > 0 ? "trend-up" : "trend-down";
}

// Назначить программу: своя программа тренера или готовый шаблон,
// по желанию — сразу разложить по календарю клиента
function AssignProgramDialog({
  clientId,
  clientName,
  onClose,
  onDone,
}: {
  clientId: number;
  clientName: string;
  onClose: () => void;
  onDone: (programId: number) => void;
}) {
  const toast = useToast();
  const sources = useAsync(
    () => Promise.all([programsApi.list(), programsApi.templates()]),
    [],
  );
  const [programId, setProgramId] = useState<number | null>(null);
  const [withSchedule, setWithSchedule] = useState(true);
  const [startDate, setStartDate] = useState(today());
  const [weeks, setWeeks] = useState(4);
  const [weekdays, setWeekdays] = useState<number[]>([0, 2, 4]);
  const [busy, setBusy] = useState(false);

  const own: Program[] = sources.data?.[0].filter((program) => !program.assigned_by) ?? [];
  const templates: ProgramDetail[] = sources.data?.[1] ?? [];
  const chosen = programId ?? own[0]?.id ?? templates[0]?.id ?? null;

  const toggleDay = (day: number) =>
    setWeekdays((current) =>
      current.includes(day) ? current.filter((item) => item !== day) : [...current, day],
    );

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (chosen === null) return;
    setBusy(true);

    try {
      const result = await coach.assign(
        clientId,
        chosen,
        withSchedule ? { start_date: startDate, weeks, weekdays } : null,
      );
      toast.success(
        result.workouts_created > 0
          ? `Программа назначена, запланировано ${result.workouts_created} ${plural(result.workouts_created, "тренировка", "тренировки", "тренировок")}`
          : "Программа назначена",
      );
      onDone(result.program_id);
    } catch (error) {
      toast.error(error);
      setBusy(false);
    }
  };

  return (
    <Modal title="Назначить программу" onClose={onClose}>
      {sources.error ? (
        <ErrorNote error={sources.error} onRetry={() => void sources.reload()} />
      ) : !sources.data ? (
        <Loading />
      ) : own.length === 0 && templates.length === 0 ? (
        <p className="modal-text">
          Сначала создайте программу в разделе <a href="#/programs">Программы</a> — она станет
          шаблоном для клиентов.
        </p>
      ) : (
        <form className="form" onSubmit={submit}>
          <p className="muted small">
            Клиент: {clientName}. У него появится копия программы. Её ведёте вы: клиент
            занимается по ней, но менять не может. Ваш шаблон не изменится.
          </p>

          <Field label="Программа">
            <select
              value={chosen ?? ""}
              onChange={(event) => setProgramId(Number(event.target.value))}
            >
              {own.length > 0 && (
                <optgroup label="Мои программы">
                  {own.map((program) => (
                    <option key={program.id} value={program.id}>{program.name}</option>
                  ))}
                </optgroup>
              )}
              {templates.length > 0 && (
                <optgroup label="Готовые программы">
                  {templates.map((program) => (
                    <option key={program.id} value={program.id}>{program.name}</option>
                  ))}
                </optgroup>
              )}
            </select>
          </Field>

          <label className="toggle">
            <input
              type="checkbox"
              checked={withSchedule}
              onChange={(event) => setWithSchedule(event.target.checked)}
            />
            Сразу разложить по календарю клиента
          </label>

          {withSchedule && (
            <>
              <fieldset className="field">
                <legend className="field-label">Дни недели</legend>
                <div className="chips">
                  {WEEKDAYS_SHORT.map((name, index) => (
                    <button
                      key={name}
                      type="button"
                      className={`chip ${weekdays.includes(index) ? "active" : ""}`}
                      aria-pressed={weekdays.includes(index)}
                      onClick={() => toggleDay(index)}
                    >
                      {name}
                    </button>
                  ))}
                </div>
              </fieldset>
              <div className="form-row">
                <Field label="Начиная с">
                  <input
                    type="date"
                    required
                    value={startDate}
                    onChange={(event) => setStartDate(event.target.value)}
                  />
                </Field>
                <Field label="Недель">
                  <input
                    type="number"
                    min={1}
                    max={52}
                    required
                    value={weeks}
                    onChange={(event) => setWeeks(Number(event.target.value))}
                  />
                </Field>
              </div>
            </>
          )}

          <div className="modal-actions">
            <Button onClick={onClose}>Отмена</Button>
            <Button
              variant="primary"
              type="submit"
              busy={busy}
              disabled={chosen === null || (withSchedule && weekdays.length === 0)}
            >
              Назначить
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}

function Notes({ clientId }: { clientId: number }) {
  const toast = useToast();
  const [confirmDialog, confirm] = useConfirm();
  const notes = useAsync(() => coach.notes(clientId), [clientId]);
  const [text, setText] = useState("");
  const [shared, setShared] = useState(false);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<CoachNote | null>(null);
  const [editText, setEditText] = useState("");

  const add = async (event: FormEvent) => {
    event.preventDefault();
    if (!text.trim()) return;
    setBusy(true);

    try {
      const note = await coach.addNote(clientId, text, shared);
      notes.setData([note, ...(notes.data ?? [])]);
      setText("");
      if (shared) toast.success("Заметка добавлена — клиент её видит");
      setShared(false);
    } catch (error) {
      toast.error(error);
    } finally {
      setBusy(false);
    }
  };

  const save = async (event: FormEvent) => {
    event.preventDefault();
    if (!editing || !editText.trim()) return;

    try {
      const updated = await coach.updateNote(editing.id, { text: editText });
      notes.setData((notes.data ?? []).map((note) => (note.id === updated.id ? updated : note)));
      setEditing(null);
    } catch (error) {
      toast.error(error);
    }
  };

  const toggleShared = async (note: CoachNote) => {
    try {
      const updated = await coach.updateNote(note.id, { shared: !note.shared });
      notes.setData((notes.data ?? []).map((item) => (item.id === updated.id ? updated : item)));
      toast.success(updated.shared ? "Клиент теперь видит заметку" : "Заметка скрыта от клиента");
    } catch (error) {
      toast.error(error);
    }
  };

  const remove = async (note: CoachNote) => {
    if (!(await confirm("Удалить заметку?", "Удалить"))) return;

    try {
      await coach.removeNote(note.id);
      notes.setData((notes.data ?? []).filter((item) => item.id !== note.id));
    } catch (error) {
      toast.error(error);
    }
  };

  return (
    <section className="block notes" aria-labelledby="notes-title">
      <h2 className="block-title" id="notes-title">Заметки тренера</h2>
      <p className="muted small">
        Обычные заметки видите только вы. Заметки с отметкой «Видна клиенту» клиент видит у себя
        на главной и в профиле.
      </p>

      <form className="note-form" onSubmit={add}>
        <textarea
          rows={3}
          maxLength={5000}
          placeholder="Как прошла встреча, самочувствие, что поменять в плане…"
          id="new-note"
          aria-label="Новая заметка"
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
        <div className="note-form-row">
          <label className="toggle">
            <input
              type="checkbox"
              checked={shared}
              onChange={(event) => setShared(event.target.checked)}
            />
            Показать клиенту
          </label>
          <Button variant="primary" type="submit" busy={busy} disabled={!text.trim()}>
            Добавить заметку
          </Button>
        </div>
      </form>

      {notes.error && <ErrorNote error={notes.error} onRetry={() => void notes.reload()} />}

      {notes.data && notes.data.length > 0 && (
        <ul className="note-list">
          {notes.data.map((note) => (
            <li key={note.id} className={note.shared ? "note is-shared" : "note"}>
              {editing?.id === note.id ? (
                <form className="note-form" onSubmit={save}>
                  <textarea
                    rows={3}
                    maxLength={5000}
                    aria-label="Текст заметки"
                    value={editText}
                    autoFocus
                    onChange={(event) => setEditText(event.target.value)}
                  />
                  <div className="note-actions">
                    <Button small onClick={() => setEditing(null)}>Отмена</Button>
                    <Button small variant="primary" type="submit" disabled={!editText.trim()}>
                      Сохранить
                    </Button>
                  </div>
                </form>
              ) : (
                <>
                  <div className="note-head">
                    <time className="note-date" dateTime={note.created_at}>
                      {formatDay(note.created_at.slice(0, 10))}
                    </time>
                    {note.shared && <span className="note-shared">Видна клиенту</span>}
                    <span className="note-tools">
                      <button
                        type="button"
                        className="note-share"
                        onClick={() => void toggleShared(note)}
                      >
                        {note.shared ? "Скрыть от клиента" : "Показать клиенту"}
                      </button>
                      <IconButton
                        icon="edit"
                        label="Изменить заметку"
                        onClick={() => {
                          setEditing(note);
                          setEditText(note.text);
                        }}
                      />
                      <IconButton icon="trash" label="Удалить заметку" onClick={() => void remove(note)} />
                    </span>
                  </div>
                  <p className="note-text">{note.text}</p>
                </>
              )}
            </li>
          ))}
        </ul>
      )}

      {confirmDialog}
    </section>
  );
}
