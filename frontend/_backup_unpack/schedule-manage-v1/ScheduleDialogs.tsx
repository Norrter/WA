// Диалоги планирования: одна тренировка, автоплан на несколько недель,
// перенос тренировки и управление всем планом (сдвиг и очистка)

import { useEffect, useState, type FormEvent } from "react";

import { workouts, type PlanFilter } from "../api";
import type { ProgramDetail, ScheduledWorkout, ScheduleInput } from "../api/types";
import { addDays, formatDayWithWeekday, today, WEEKDAYS_SHORT } from "../lib/dates";
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
  generate,
}: {
  programs: ProgramDetail[];
  programId?: number;
  onClose: () => void;
  onDone: () => void;
  // Своя раскладка, например тренер раскладывает программу клиента.
  // Возвращает, сколько тренировок создано
  generate?: (programId: number, schedule: ScheduleInput) => Promise<number>;
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
      const schedule = { start_date: startDate, weeks, weekdays };
      const created = generate
        ? await generate(programId, schedule)
        : (await workouts.generate({ program_id: programId, ...schedule })).length;
      toast.success(
        created === 0
          ? "Новых тренировок нет: эти даты уже заняты"
          : `Запланировано ${created} ${plural(created, "тренировка", "тренировки", "тренировок")}`,
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

// ----- Перенос одной тренировки -----

export function MoveWorkoutDialog({
  workout,
  title,
  onClose,
  onDone,
}: {
  workout: ScheduledWorkout;
  title: string;
  onClose: () => void;
  onDone: () => void;
}) {
  const toast = useToast();
  const now = today();
  const from = workout.scheduled_date;
  const [date, setDate] = useState(addDays(from < now ? now : from, 1));
  const [busy, setBusy] = useState(false);

  const quick: { label: string; value: string }[] = [
    ...(from !== now ? [{ label: "На сегодня", value: now }] : []),
    { label: "+1 день", value: addDays(from, 1) },
    { label: "+2 дня", value: addDays(from, 2) },
    { label: "+1 неделя", value: addDays(from, 7) },
  ];

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);

    try {
      await workouts.patch(workout.id, { scheduled_date: date });
      toast.success(`Перенесено на ${formatDayWithWeekday(date)}`);
      onDone();
    } catch (error) {
      toast.error(error);
      setBusy(false);
    }
  };

  return (
    <Modal title="Перенести тренировку" onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <p className="modal-text">
          <strong>{title}</strong> · сейчас стоит на {formatDayWithWeekday(from)}
        </p>
        <div className="chips">
          {quick.map((item) => (
            <button
              key={item.label}
              type="button"
              className={`chip ${date === item.value ? "active" : ""}`}
              aria-pressed={date === item.value}
              onClick={() => setDate(item.value)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <Field label="Новая дата">
          <input type="date" required value={date} onChange={(event) => setDate(event.target.value)} />
        </Field>
        <div className="modal-actions">
          <Button onClick={onClose}>Отмена</Button>
          <Button variant="primary" type="submit" busy={busy} disabled={!date || date === from}>
            Перенести
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// ----- Управление всем планом: сдвинуть или очистить -----

type ClearPeriod = "future" | "month" | "custom";

export function ManagePlanDialog({
  programs,
  month,
  onClose,
  onDone,
}: {
  programs: ProgramDetail[];
  // месяц, который сейчас открыт в календаре
  month: { from: string; to: string; title: string };
  onClose: () => void;
  onDone: () => void;
}) {
  const toast = useToast();
  const now = today();
  const [mode, setMode] = useState<"shift" | "clear">("shift");
  const [programId, setProgramId] = useState<number | "">("");

  // сдвиг
  const [shiftFrom, setShiftFrom] = useState(now);
  const [days, setDays] = useState(7);

  // очистка
  const [period, setPeriod] = useState<ClearPeriod>("future");
  const [clearFrom, setClearFrom] = useState(now);
  const [clearTo, setClearTo] = useState(addDays(now, 30));

  const [count, setCount] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);

  const filter = (): PlanFilter => {
    const program_id = programId === "" ? null : programId;

    if (mode === "shift") return { date_from: shiftFrom, program_id };
    if (period === "future") return { date_from: now, program_id };
    if (period === "month") {
      return { date_from: month.from < now ? now : month.from, date_to: month.to, program_id };
    }
    return { date_from: clearFrom, date_to: clearTo, program_id };
  };

  const valid =
    mode === "shift"
      ? Boolean(shiftFrom) && Number.isInteger(days) && days !== 0 && Math.abs(days) <= 90
      : period !== "custom" || (Boolean(clearFrom) && Boolean(clearTo) && clearTo >= clearFrom);

  // Сколько тренировок затронет — считаем на сервере, ничего не меняя
  const key = JSON.stringify([mode, programId, shiftFrom, days, period, clearFrom, clearTo]);
  useEffect(() => {
    if (!valid) {
      setCount(null);
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(() => {
      const data = { ...filter(), dry_run: true };
      const request = mode === "shift" ? workouts.shift({ ...data, days }) : workouts.clear(data);
      request
        .then((result) => !cancelled && setCount(result.count))
        .catch(() => !cancelled && setCount(null));
    }, 250);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, valid]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);

    try {
      if (mode === "shift") {
        const { count: moved } = await workouts.shift({ ...filter(), days });
        toast.success(
          moved === 0
            ? "Сдвигать нечего"
            : `Сдвинуто ${moved} ${plural(moved, "тренировка", "тренировки", "тренировок")}`,
        );
      } else {
        const { count: removed } = await workouts.clear(filter());
        toast.success(
          removed === 0
            ? "Удалять нечего"
            : `Удалено ${removed} ${plural(removed, "тренировка", "тренировки", "тренировок")}`,
        );
      }
      onDone();
    } catch (error) {
      toast.error(error);
      setBusy(false);
    }
  };

  const countText =
    count === null
      ? "Считаем…"
      : count === 0
        ? "Под условия не попала ни одна запланированная тренировка."
        : `${mode === "shift" ? "Сдвинется" : "Удалится"} ${count} ${plural(
            count,
            "запланированная тренировка",
            "запланированные тренировки",
            "запланированных тренировок",
          )}.`;

  const shiftPresets = [-1, 1, 2, 7, 14];

  return (
    <Modal title="Управление планом" onClose={onClose}>
      <form className="form plan-manage" onSubmit={submit}>
        <div className="segmented plan-mode" role="tablist" aria-label="Что сделать">
          <button
            type="button"
            role="tab"
            aria-selected={mode === "shift"}
            className={mode === "shift" ? "active" : ""}
            onClick={() => setMode("shift")}
          >
            Сдвинуть
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "clear"}
            className={mode === "clear" ? "active" : ""}
            onClick={() => setMode("clear")}
          >
            Очистить
          </button>
        </div>

        {mode === "shift" ? (
          <>
            <p className="muted small">
              Например, неделю не получилось тренироваться — сдвиньте всё, что дальше, на 7 дней.
            </p>
            <Field label="Начиная с даты">
              <input type="date" required value={shiftFrom} onChange={(event) => setShiftFrom(event.target.value)} />
            </Field>
            <fieldset className="field">
              <legend className="field-label">На сколько дней</legend>
              <div className="chips">
                {shiftPresets.map((value) => (
                  <button
                    key={value}
                    type="button"
                    className={`chip ${days === value ? "active" : ""}`}
                    aria-pressed={days === value}
                    onClick={() => setDays(value)}
                  >
                    {value > 0 ? "+" : "−"}
                    {Math.abs(value) === 7
                      ? "1 неделя"
                      : Math.abs(value) === 14
                        ? "2 недели"
                        : `${Math.abs(value)} ${plural(Math.abs(value), "день", "дня", "дней")}`}
                  </button>
                ))}
              </div>
              <input
                type="number"
                min={-90}
                max={90}
                step={1}
                value={Number.isNaN(days) ? "" : days}
                aria-label="Своё число дней: плюс — вперёд, минус — назад"
                onChange={(event) => setDays(Number(event.target.value))}
              />
              <span className="field-hint">Плюс — вперёд, минус — назад</span>
            </fieldset>
          </>
        ) : (
          <>
            <fieldset className="field">
              <legend className="field-label">Что удалить</legend>
              <div className="chips">
                {(
                  [
                    ["future", "Всё будущее"],
                    ["month", capitalizeFirst(month.title)],
                    ["custom", "Свой период"],
                  ] as [ClearPeriod, string][]
                ).map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    className={`chip ${period === value ? "active" : ""}`}
                    aria-pressed={period === value}
                    onClick={() => setPeriod(value)}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </fieldset>
            {period === "custom" && (
              <div className="form-row">
                <Field label="С">
                  <input type="date" required value={clearFrom} onChange={(event) => setClearFrom(event.target.value)} />
                </Field>
                <Field label="По">
                  <input type="date" required value={clearTo} onChange={(event) => setClearTo(event.target.value)} />
                </Field>
              </div>
            )}
          </>
        )}

        <Field label="Программа">
          <select
            value={programId}
            onChange={(event) => setProgramId(event.target.value === "" ? "" : Number(event.target.value))}
          >
            <option value="">Все программы</option>
            {programs.map((program) => (
              <option key={program.id} value={program.id}>{program.name}</option>
            ))}
          </select>
        </Field>

        <div className={`plan-preview ${mode === "clear" && count ? "is-danger" : ""}`} role="status">
          <strong>{valid ? countText : "Проверьте даты"}</strong>
          <span>Выполненные, пропущенные и уже начатые тренировки не трогаем.</span>
        </div>

        <div className="modal-actions">
          <Button onClick={onClose}>Отмена</Button>
          <Button
            variant={mode === "clear" ? "danger" : "primary"}
            type="submit"
            busy={busy}
            disabled={!valid || !count}
          >
            {mode === "shift"
              ? "Сдвинуть"
              : count
                ? `Удалить · ${count}`
                : "Удалить"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function capitalizeFirst(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}
