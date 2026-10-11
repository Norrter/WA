// Диалоги планирования: одна тренировка и автоплан на несколько недель

import { useState, type FormEvent } from "react";

import { workouts } from "../api";
import type { ProgramDetail } from "../api/types";
import { WEEKDAYS_SHORT, today } from "../lib/dates";
import { plural } from "../lib/format";
import { useToast } from "./Toast";
import { Button, Field, Modal } from "./ui";

export function PlanWorkoutDialog({
  programs,
  date,
  onClose,
  onDone,
}: {
  programs: ProgramDetail[];
  date?: string;
  onClose: () => void;
  onDone: () => void;
}) {
  const toast = useToast();
  const usable = programs.filter((program) => program.days.length > 0);
  const [programId, setProgramId] = useState(usable[0]?.id ?? 0);
  const program = usable.find((item) => item.id === programId);
  const [dayId, setDayId] = useState(program?.days[0]?.id ?? 0);
  const [scheduledDate, setScheduledDate] = useState(date ?? today());
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);

    try {
      await workouts.create({
        program_id: programId,
        program_day_id: dayId,
        scheduled_date: scheduledDate,
      });
      toast.success("Тренировка запланирована");
      onDone();
    } catch (error) {
      toast.error(error);
      setBusy(false);
    }
  };

  return (
    <Modal title="Запланировать тренировку" onClose={onClose}>
      {usable.length === 0 ? (
        <p className="modal-text">
          Нужна программа хотя бы с одним днём. <a href="#/programs">Создайте программу</a>.
        </p>
      ) : (
        <form className="form" onSubmit={submit}>
          <Field label="Программа">
            <select
              value={programId}
              onChange={(event) => {
                const id = Number(event.target.value);
                setProgramId(id);
                setDayId(usable.find((item) => item.id === id)?.days[0]?.id ?? 0);
              }}
            >
              {usable.map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
          </Field>
          <Field label="День программы">
            <select value={dayId} onChange={(event) => setDayId(Number(event.target.value))}>
              {program?.days.map((day) => (
                <option key={day.id} value={day.id}>{day.name}</option>
              ))}
            </select>
          </Field>
          <Field label="Дата">
            <input
              type="date"
              required
              value={scheduledDate}
              onChange={(event) => setScheduledDate(event.target.value)}
            />
          </Field>
          <div className="modal-actions">
            <Button onClick={onClose}>Отмена</Button>
            <Button variant="primary" type="submit" busy={busy}>Запланировать</Button>
          </div>
        </form>
      )}
    </Modal>
  );
}

export function AutoPlanDialog({
  programs,
  programId: initialProgramId,
  onClose,
  onDone,
}: {
  programs: ProgramDetail[];
  programId?: number;
  onClose: () => void;
  onDone: () => void;
}) {
  const toast = useToast();
  const usable = programs.filter((program) => program.days.length > 0);
  const [programId, setProgramId] = useState(initialProgramId ?? usable[0]?.id ?? 0);
  const [startDate, setStartDate] = useState(today());
  const [weeks, setWeeks] = useState(4);
  const [weekdays, setWeekdays] = useState<number[]>([0, 2, 4]);
  const [busy, setBusy] = useState(false);

  const program = usable.find((item) => item.id === programId);

  const toggleDay = (day: number) =>
    setWeekdays((current) =>
      current.includes(day) ? current.filter((item) => item !== day) : [...current, day],
    );

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);

    try {
      const created = await workouts.generate({
        program_id: programId,
        start_date: startDate,
        weeks,
        weekdays,
      });
      toast.success(
        created.length === 0
          ? "Новых тренировок нет: эти даты уже заняты"
          : `Запланировано ${created.length} ${plural(created.length, "тренировка", "тренировки", "тренировок")}`,
      );
      onDone();
    } catch (error) {
      toast.error(error);
      setBusy(false);
    }
  };

  return (
    <Modal title="Разложить программу по календарю" onClose={onClose}>
      {usable.length === 0 ? (
        <p className="modal-text">
          Нужна программа хотя бы с одним днём. <a href="#/programs">Создайте программу</a>.
        </p>
      ) : (
        <form className="form" onSubmit={submit}>
          <Field label="Программа">
            <select value={programId} onChange={(event) => setProgramId(Number(event.target.value))}>
              {usable.map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
          </Field>

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

          {program && (
            <p className="muted">
              Дни программы пойдут по кругу: {program.days.map((day) => day.name).join(", ")}.
              Даты, на которые эта программа уже стоит, пропускаются.
            </p>
          )}

          <div className="modal-actions">
            <Button onClick={onClose}>Отмена</Button>
            <Button
              variant="primary"
              type="submit"
              busy={busy}
              disabled={weekdays.length === 0}
            >
              Запланировать
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}
