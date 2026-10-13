// Тренировка клиента глазами тренера: план, сделанные подходы, оценка
// клиента и комментарий тренера. Менять подходы тренер не может.

import { useState, type FormEvent } from "react";

import { coach } from "../api";
import type { WorkoutDetail, WorkoutExerciseDetail } from "../api/types";
import { FeedbackLine } from "../components/Feedback";
import { CoachMessage } from "../components/MyCoach";
import { useScene } from "../components/Scene";
import { useToast } from "../components/Toast";
import { Button, Empty, ErrorNote, Loading, PageHeader, StatusPill } from "../components/ui";
import { formatDayWithWeekday, today } from "../lib/dates";
import { formatNumber, formatReps, formatWeight } from "../lib/format";
import { useAsync } from "../lib/useAsync";

export function CoachWorkoutPage({ id, workoutId }: { id: number; workoutId: number }) {
  useScene("throne");

  const now = today();
  const state = useAsync(
    () => Promise.all([coach.workout(id, workoutId), coach.card(id, now, now)]),
    [id, workoutId],
  );

  if (state.error) {
    return (
      <div className="page">
        <ErrorNote error={state.error} onRetry={() => void state.reload()} />
        <p>
          <a href={`#/coach/clients/${id}`}>К карточке клиента</a>
        </p>
      </div>
    );
  }

  if (!state.data) return <Loading />;

  const [workout, card] = state.data;
  const setWorkout = (next: WorkoutDetail) => state.setData([next, card]);

  const done = workout.exercises.flatMap((item) => item.performed_sets.filter((set) => set.completed));
  const volume = done.reduce((sum, set) => sum + set.weight * set.reps, 0);
  const planned = workout.exercises.reduce((sum, item) => sum + item.sets, 0);
  const hasFeedback =
    workout.wellbeing !== null || workout.difficulty !== null || !!workout.feedback_comment;

  return (
    <div className="page page-workout coach-workout">
      <PageHeader
        back={{ href: `#/coach/clients/${id}`, label: card.client.username }}
        eyebrow={`${card.client.username} · ${formatDayWithWeekday(workout.scheduled_date)}`}
        title={workout.program_day_name}
        subtitle={
          <>
            {workout.program_name}
            <StatusPill status={workout.status} />
          </>
        }
      />

      <dl className="figures figures-card">
        <div>
          <dt>Подходы</dt>
          <dd>
            {done.length}
            {planned > 0 && <small> / {planned}</small>}
          </dd>
        </div>
        <div>
          <dt>Поднято, кг</dt>
          <dd>{formatNumber(volume)}</dd>
        </div>
        <div>
          <dt>Упражнений</dt>
          <dd>{workout.exercises.length}</dd>
        </div>
      </dl>

      <section className="block" aria-labelledby="cw-feedback-title">
        <h2 className="block-title" id="cw-feedback-title">Оценка клиента</h2>
        {hasFeedback ? (
          <FeedbackLine feedback={workout} />
        ) : (
          <p className="muted">
            {workout.status === "completed"
              ? "Клиент не оценил тренировку."
              : "Оценка появится, когда клиент завершит тренировку."}
          </p>
        )}
      </section>

      <section className="block" aria-labelledby="cw-exercises-title">
        <h2 className="block-title" id="cw-exercises-title">Упражнения</h2>
        {workout.exercises.length === 0 ? (
          <Empty title="В тренировке нет упражнений" />
        ) : (
          <ol className="cw-exercises">
            {workout.exercises.map((item, index) => (
              <ExerciseResult key={`${item.program_exercise_id ?? "x"}-${item.exercise.id}`} item={item} index={index} />
            ))}
          </ol>
        )}
      </section>

      <CommentEditor
        clientId={id}
        workout={workout}
        onSaved={(comment) => setWorkout({ ...workout, ...comment })}
      />
    </div>
  );
}

function ExerciseResult({ item, index }: { item: WorkoutExerciseDetail; index: number }) {
  const plan =
    item.program_exercise_id === null
      ? "нет в плане — только сделанные подходы"
      : `План: ${item.sets} × ${formatReps(item.target_reps, item.target_reps_max)}${
          item.target_weight ? ` · ${formatWeight(item.target_weight)}` : ""
        }`;
  const done = item.performed_sets.filter((set) => set.completed).length;

  return (
    <li className="cw-exercise">
      <div className="cw-exercise-head">
        <span className="wx-index">{index + 1}</span>
        <span className="cw-exercise-name">{item.exercise.name}</span>
        <span className="wx-count">
          {done}/{item.sets}
        </span>
      </div>
      <p className="cw-plan">{plan}</p>
      {item.performed_sets.length === 0 ? (
        <p className="cw-none">Подходов не записано</p>
      ) : (
        <ol className="cw-sets">
          {item.performed_sets.map((set) => (
            <li key={set.id} className={set.completed ? "cw-set" : "cw-set is-missed"}>
              <span className="cw-set-number">{set.set_number}</span>
              {formatWeight(set.weight)} × {set.reps}
              {!set.completed && <span className="cw-set-flag">не выполнен</span>}
            </li>
          ))}
        </ol>
      )}
    </li>
  );
}

function CommentEditor({
  clientId,
  workout,
  onSaved,
}: {
  clientId: number;
  workout: WorkoutDetail;
  onSaved: (comment: Pick<WorkoutDetail, "coach_comment" | "coach_comment_at" | "coach_comment_author">) => void;
}) {
  const toast = useToast();
  const [editing, setEditing] = useState(!workout.coach_comment);
  const [text, setText] = useState(workout.coach_comment ?? "");
  const [busy, setBusy] = useState(false);

  const save = async (value: string) => {
    setBusy(true);

    try {
      const saved = await coach.comment(clientId, workout.id, value);
      onSaved(saved);
      setText(saved.coach_comment ?? "");
      setEditing(!saved.coach_comment);
      toast.success(saved.coach_comment ? "Комментарий сохранён — клиент его видит" : "Комментарий удалён");
    } catch (error) {
      toast.error(error);
    } finally {
      setBusy(false);
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void save(text);
  };

  return (
    <section className="block" aria-labelledby="cw-comment-title">
      <h2 className="block-title" id="cw-comment-title">Комментарий тренера</h2>

      {!editing && workout.coach_comment ? (
        <>
          <CoachMessage
            label={`Видит клиент${workout.coach_comment_author ? ` · ${workout.coach_comment_author}` : ""}`}
            date={workout.coach_comment_at}
            text={workout.coach_comment}
          />
          <div className="comment-form-actions cw-comment-tools">
            <Button small icon="edit" onClick={() => setEditing(true)}>
              Изменить
            </Button>
            <Button small variant="ghost" busy={busy} onClick={() => void save("")}>
              Удалить
            </Button>
          </div>
        </>
      ) : (
        <form className="comment-form" onSubmit={submit}>
          <p className="muted small">
            Клиент увидит комментарий в этой тренировке. Например: что получилось, что поменять в
            следующий раз.
          </p>
          <textarea
            rows={3}
            maxLength={2000}
            placeholder="Отлично! В следующий раз добавь 2,5 кг в жиме…"
            aria-label="Комментарий к тренировке"
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
          <div className="comment-form-actions">
            <Button variant="primary" type="submit" busy={busy} disabled={!text.trim()}>
              {workout.coach_comment ? "Сохранить" : "Отправить клиенту"}
            </Button>
            {workout.coach_comment && (
              <Button
                onClick={() => {
                  setText(workout.coach_comment ?? "");
                  setEditing(false);
                }}
              >
                Отмена
              </Button>
            )}
          </div>
        </form>
      )}
    </section>
  );
}
