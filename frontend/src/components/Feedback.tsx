// Оценка тренировки: самочувствие (1–5), сложность (1–10), комментарий

import { useState, type FormEvent } from "react";

import { workouts } from "../api";
import type { WorkoutFeedback } from "../api/types";
import { useToast } from "./Toast";
import { Button, Field, Modal } from "./ui";

export const WELLBEING_LABELS = ["Плохо", "Так себе", "Нормально", "Хорошо", "Отлично"];

export function wellbeingLabel(value: number): string {
  return WELLBEING_LABELS[Math.round(value) - 1] ?? "";
}

// Короткая подпись: «Хорошо · сложность 8/10»
export function FeedbackLine({ feedback }: { feedback: Partial<WorkoutFeedback> }) {
  const parts = [];

  if (feedback.wellbeing) parts.push(wellbeingLabel(feedback.wellbeing));
  if (feedback.difficulty) parts.push(`сложность ${feedback.difficulty}/10`);

  if (parts.length === 0 && !feedback.feedback_comment) return null;

  return (
    <span className="feedback-line">
      {parts.join(" · ")}
      {feedback.feedback_comment && (
        <span className="feedback-comment">«{feedback.feedback_comment}»</span>
      )}
    </span>
  );
}

function Scale({
  label,
  hint,
  count,
  value,
  onChange,
  labels,
}: {
  label: string;
  hint: string;
  count: number;
  value: number | null;
  onChange: (value: number | null) => void;
  labels?: string[];
}) {
  return (
    <fieldset className="scale">
      <legend className="field-label">{label}</legend>
      <div className="scale-options" role="radiogroup" aria-label={label}>
        {Array.from({ length: count }, (_, index) => index + 1).map((option) => (
          <button
            key={option}
            type="button"
            role="radio"
            aria-checked={value === option}
            className={`scale-option ${value === option ? "active" : ""}`}
            title={labels?.[option - 1]}
            onClick={() => onChange(value === option ? null : option)}
          >
            {option}
          </button>
        ))}
      </div>
      <span className="field-hint">
        {value !== null && labels ? labels[value - 1] : hint}
      </span>
    </fieldset>
  );
}

export function FeedbackDialog({
  workoutId,
  initial,
  onClose,
  onSaved,
}: {
  workoutId: number;
  initial: WorkoutFeedback;
  onClose: () => void;
  onSaved: (feedback: WorkoutFeedback) => void;
}) {
  const toast = useToast();
  const [wellbeing, setWellbeing] = useState(initial.wellbeing);
  const [difficulty, setDifficulty] = useState(initial.difficulty);
  const [comment, setComment] = useState(initial.feedback_comment ?? "");
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);

    try {
      const saved = await workouts.patch(workoutId, {
        wellbeing,
        difficulty,
        feedback_comment: comment.trim() || null,
      });
      onSaved({
        wellbeing: saved.wellbeing,
        difficulty: saved.difficulty,
        feedback_comment: saved.feedback_comment,
        feedback_at: saved.feedback_at,
      });
    } catch (error) {
      toast.error(error);
      setBusy(false);
    }
  };

  return (
    <Modal title="Как прошла тренировка?" onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <Scale
          label="Самочувствие"
          hint="1 — плохо, 5 — отлично"
          count={5}
          value={wellbeing}
          onChange={setWellbeing}
          labels={WELLBEING_LABELS}
        />
        <Scale
          label="Сложность"
          hint="1 — очень легко, 10 — на пределе"
          count={10}
          value={difficulty}
          onChange={setDifficulty}
        />
        <Field label="Комментарий" hint="Необязательно. Если у вас есть тренер, он это увидит.">
          <textarea
            rows={3}
            maxLength={2000}
            placeholder="Что получилось, что мешало, как самочувствие"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
          />
        </Field>
        <div className="modal-actions">
          <Button onClick={onClose}>Не сейчас</Button>
          <Button variant="primary" type="submit" busy={busy}>Сохранить</Button>
        </div>
      </form>
    </Modal>
  );
}
