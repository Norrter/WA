// Питание: норма КБЖУ по антропометрии и дневник еды по дням

import { useState, type FormEvent } from "react";

import { bodyWeight as bodyWeightApi, nutrition } from "../api";
import type {
  Activity,
  Anthropometry,
  FoodEntry,
  Goal,
  Macros,
  Meal,
  NutritionDay,
  NutritionDaySummary,
  NutritionProfile,
  Sex,
} from "../api/types";
import { useAuth } from "../components/Auth";
import { BarChart } from "../components/Charts";
import { FoodDialog, macrosLine } from "../components/FoodDialog";
import { Icon } from "../components/Icon";
import { useScene } from "../components/Scene";
import { useToast } from "../components/Toast";
import { Button, ErrorNote, Field, IconButton, Loading, PageHeader } from "../components/ui";
import { addDays, formatDay, formatDayWithWeekday, relativeDay, today, weekdayIndex, WEEKDAYS_SHORT } from "../lib/dates";
import { formatNumber } from "../lib/format";
import {
  ACTIVITIES,
  amountText,
  calculateNorm,
  GOALS,
  mealByTime,
  MEALS,
  parseAmount,
  round1,
} from "../lib/nutrition";
import { useAsync } from "../lib/useAsync";

const MACROS: { key: keyof Macros; label: string; short: string; unit: string }[] = [
  { key: "protein", label: "Белки", short: "Б", unit: "г" },
  { key: "fat", label: "Жиры", short: "Ж", unit: "г" },
  { key: "carbs", label: "Углеводы", short: "У", unit: "г" },
];

export function NutritionPage() {
  useScene("pillars");

  const now = today();
  const [date, setDate] = useState(now);
  const [dialog, setDialog] = useState<{ meal: Meal; entry?: FoodEntry } | null>(null);
  const [editingNorm, setEditingNorm] = useState(false);

  const profileState = useAsync(() => nutrition.profile(), []);
  const dayState = useAsync(() => nutrition.day(date), [date]);
  const weekState = useAsync(() => nutrition.summary(addDays(date, -6), date), [date]);

  const error = profileState.error ?? dayState.error;

  if (error) {
    return (
      <ErrorNote
        error={error}
        onRetry={() => {
          void profileState.reload();
          void dayState.reload();
        }}
      />
    );
  }

  if (profileState.data === undefined || !dayState.data) return <Loading />;

  const profile = profileState.data;
  const day = dayState.data;
  const showCalculator = !profile || editingNorm;

  const refresh = () => {
    setDialog(null);
    void dayState.reload();
    void weekState.reload();
  };

  const calculator = (
    <NormCalculator
      profile={profile}
      onCancel={profile ? () => setEditingNorm(false) : undefined}
      onSaved={(saved) => {
        profileState.setData(saved);
        setEditingNorm(false);
        void dayState.reload();
      }}
    />
  );

  return (
    <div className="page nutrition-page">
      <PageHeader eyebrow="Норма и дневник" title="Питание" />

      {!profile && calculator}

      <section className="block" aria-labelledby="diary-title">
        <DaySwitch date={date} onChange={setDate} titleId="diary-title" />

        <DayTotals day={day} />

        <div className="meals">
          {MEALS.map((meal) => (
            <MealBlock
              key={meal.value}
              label={meal.label}
              entries={day.entries.filter((entry) => entry.meal === meal.value)}
              onAdd={() => setDialog({ meal: meal.value })}
              onOpen={(entry) => setDialog({ meal: entry.meal, entry })}
            />
          ))}
        </div>

        <Button
          variant="primary"
          icon="plus"
          className="btn-block nutrition-add"
          onClick={() => setDialog({ meal: date === now ? mealByTime() : "lunch" })}
        >
          Добавить еду
        </Button>
      </section>

      {weekState.data && (
        <WeekBlock summary={weekState.data} end={date} target={day.targets?.kcal ?? null} />
      )}

      {profile &&
        (showCalculator ? (
          calculator
        ) : (
          <NormSummary profile={profile} onEdit={() => setEditingNorm(true)} />
        ))}

      {dialog && (
        <FoodDialog
          date={date}
          meal={dialog.meal}
          entry={dialog.entry}
          onClose={() => setDialog(null)}
          onSaved={refresh}
        />
      )}
    </div>
  );
}

// ---------- Переключение дня ----------

export function DaySwitch({
  date,
  onChange,
  titleId,
}: {
  date: string;
  onChange: (date: string) => void;
  titleId: string;
}) {
  const now = today();

  return (
    <div className="day-switch">
      <IconButton icon="left" label="Предыдущий день" onClick={() => onChange(addDays(date, -1))} />
      <div className="day-switch-label">
        <h2 className="block-title" id={titleId}>
          {relativeDay(date)}
        </h2>
        {relativeDay(date) !== formatDayWithWeekday(date) && (
          <span className="muted small">{formatDayWithWeekday(date)}</span>
        )}
      </div>
      <IconButton
        icon="right"
        label="Следующий день"
        disabled={date >= now}
        onClick={() => onChange(addDays(date, 1))}
      />
    </div>
  );
}

// ---------- Итог дня ----------

function Meter({ value, target }: { value: number; target: number | null }) {
  const share = target ? Math.min(value / target, 1) : 0;
  const over = target !== null && value > target * 1.05;

  return (
    <span className={`meter ${over ? "is-over" : ""}`} aria-hidden="true">
      <span style={{ width: `${share * 100}%` }} />
    </span>
  );
}

export function DayTotals({ day }: { day: NutritionDay }) {
  const { totals, targets } = day;
  const left = targets ? Math.round(targets.kcal - totals.kcal) : null;

  return (
    <div className="panel day-totals">
      <div className="day-totals-head">
        <div>
          <span className="section-label">Съедено</span>
          <p className="day-totals-kcal">
            {formatNumber(Math.round(totals.kcal))}
            <small>{targets ? ` / ${formatNumber(targets.kcal)} ккал` : " ккал"}</small>
          </p>
        </div>
        {left !== null && (
          <div className={`day-totals-left ${left < 0 ? "is-over" : ""}`}>
            <span className="section-label">{left >= 0 ? "Осталось" : "Сверх нормы"}</span>
            <p>{formatNumber(Math.abs(left))}</p>
          </div>
        )}
      </div>
      <Meter value={totals.kcal} target={targets?.kcal ?? null} />

      <dl className="macro-totals">
        {MACROS.map((macro) => (
          <div key={macro.key}>
            <dt>{macro.label}</dt>
            <dd>
              {formatNumber(round1(totals[macro.key]))}
              <small>
                {targets ? ` / ${formatNumber(targets[macro.key])}` : ""} {macro.unit}
              </small>
            </dd>
            <Meter value={totals[macro.key]} target={targets ? targets[macro.key] : null} />
          </div>
        ))}
      </dl>

      {!targets && (
        <p className="muted small">Рассчитайте норму — здесь будет видно, сколько осталось до неё.</p>
      )}
    </div>
  );
}

// ---------- Приёмы пищи ----------

export function MealBlock({
  label,
  entries,
  onAdd,
  onOpen,
}: {
  label: string;
  entries: FoodEntry[];
  onAdd?: () => void;
  onOpen?: (entry: FoodEntry) => void;
}) {
  const kcal = entries.reduce((sum, entry) => sum + entry.kcal, 0);

  return (
    <section className="meal" aria-label={label}>
      <div className="meal-head">
        <h3>{label}</h3>
        {entries.length > 0 && <span className="meal-kcal">{formatNumber(Math.round(kcal))} ккал</span>}
        {onAdd && <IconButton icon="plus" label={`Добавить: ${label.toLowerCase()}`} onClick={onAdd} />}
      </div>
      {entries.length > 0 && (
        <ul className="meal-entries">
          {entries.map((entry) => (
            <li key={entry.id}>
              {onOpen ? (
                <button type="button" className="meal-entry" onClick={() => onOpen(entry)}>
                  <EntryContent entry={entry} />
                </button>
              ) : (
                <div className="meal-entry is-static">
                  <EntryContent entry={entry} />
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function EntryContent({ entry }: { entry: FoodEntry }) {
  return (
    <>
      <span className="meal-entry-text">
        <span className="meal-entry-name">{entry.name}</span>
        <span className="meal-entry-meta">
          {entry.grams ? `${formatNumber(entry.grams)} г · ` : ""}
          {macrosLine(entry)}
        </span>
      </span>
      <span className="meal-entry-kcal">{formatNumber(Math.round(entry.kcal))}</span>
    </>
  );
}

// ---------- Неделя ----------

export function WeekBlock({
  summary,
  end,
  target,
  idPrefix = "nutrition",
}: {
  summary: NutritionDaySummary[];
  end: string;
  target: number | null;
  idPrefix?: string;
}) {
  const byDate = new Map(summary.map((item) => [item.date, item]));
  const days = Array.from({ length: 7 }, (_, index) => addDays(end, index - 6));
  const logged = summary.filter((item) => item.entries > 0);
  const average = logged.length
    ? Math.round(logged.reduce((sum, item) => sum + item.kcal, 0) / logged.length)
    : null;
  const average3 = (key: keyof Macros) =>
    logged.length ? Math.round(logged.reduce((sum, item) => sum + item[key], 0) / logged.length) : 0;

  return (
    <section className="block" aria-labelledby={`${idPrefix}-week-title`}>
      <div className="block-head">
        <h2 className="block-title" id={`${idPrefix}-week-title`}>7 дней</h2>
        {average !== null && (
          <span className="muted small">
            в среднем {formatNumber(average)} ккал{target ? ` при норме ${formatNumber(target)}` : ""}
          </span>
        )}
      </div>
      {logged.length === 0 ? (
        <p className="muted">За эти дни записей нет.</p>
      ) : (
        <div className="panel">
          <BarChart
            items={days.map((date) => {
              const kcal = Math.round(byDate.get(date)?.kcal ?? 0);
              return {
                label: WEEKDAYS_SHORT[weekdayIndex(date)],
                value: kcal,
                title: `${formatDay(date)}: ${formatNumber(kcal)} ккал`,
              };
            })}
          />
          <p className="muted small">
            Среднее за {logged.length} {logged.length === 1 ? "день" : logged.length < 5 ? "дня" : "дней"} с
            записями: Б {average3("protein")} · Ж {average3("fat")} · У {average3("carbs")} г
          </p>
        </div>
      )}
    </section>
  );
}

// ---------- Норма ----------

function goalLabel(goal: Goal): string {
  return GOALS.find((item) => item.value === goal)?.label ?? goal;
}

function activityLabel(activity: Activity): string {
  return ACTIVITIES.find((item) => item.value === activity)?.label ?? activity;
}

export function NormSummary({ profile, onEdit }: { profile: NutritionProfile; onEdit?: () => void }) {
  const { targets, calculated } = profile;
  const custom =
    calculated !== null
    && (["kcal", "protein", "fat", "carbs"] as (keyof Macros)[]).some(
      (key) => Math.round(calculated[key]) !== Math.round(targets[key]),
    );

  return (
    <section className="block" aria-labelledby="norm-title">
      <div className="block-head">
        <h2 className="block-title" id="norm-title">Норма</h2>
        {onEdit && (
          <Button small icon="edit" onClick={onEdit}>
            Пересчитать
          </Button>
        )}
      </div>
      <div className="panel norm-summary">
        <dl className="norm-figures">
          <div>
            <dt>Ккал</dt>
            <dd>{formatNumber(targets.kcal)}</dd>
          </div>
          {MACROS.map((macro) => (
            <div key={macro.key}>
              <dt>{macro.label}</dt>
              <dd>
                {formatNumber(targets[macro.key])}
                <small> г</small>
              </dd>
            </div>
          ))}
        </dl>
        <p className="muted small">
          {goalLabel(profile.goal)} · активность {activityLabel(profile.activity).toLowerCase()} ·{" "}
          {profile.sex === "male" ? "муж." : "жен."}, {profile.age} лет, {formatNumber(profile.height_cm)} см
          {calculated ? `, ${formatNumber(calculated.weight)} кг` : ""}
        </p>
        {custom && calculated && (
          <p className="norm-note">
            Норма задана вручную. По текущему весу расчёт — {formatNumber(calculated.kcal)} ккал,{" "}
            {macrosLine(calculated)} г.
          </p>
        )}
      </div>
    </section>
  );
}

function ChoiceGrid<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
}) {
  return (
    <div className="field">
      <span className="field-label">{label}</span>
      <div className={`choice-grid choice-grid-${options.length}`} role="group" aria-label={label}>
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            className={value === option.value ? "active" : ""}
            aria-pressed={value === option.value}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function NormCalculator({
  profile,
  onCancel,
  onSaved,
}: {
  profile: NutritionProfile | null;
  onCancel?: () => void;
  onSaved: (profile: NutritionProfile) => void;
}) {
  const toast = useToast();
  const { user, setUser } = useAuth();
  const journalWeight = user?.body_weight ?? null;

  const [sex, setSex] = useState<Sex>(profile?.sex ?? "male");
  const [age, setAge] = useState(profile ? String(profile.age) : "");
  const [height, setHeight] = useState(profile ? amountText(profile.height_cm) : "");
  const [weight, setWeight] = useState(amountText(journalWeight));
  const [activity, setActivity] = useState<Activity>(profile?.activity ?? "moderate");
  const [goal, setGoal] = useState<Goal>(profile?.goal ?? "maintain");
  const [custom, setCustom] = useState(false);
  const [targets, setTargets] = useState<Record<keyof Macros, string>>({
    kcal: "",
    protein: "",
    fat: "",
    carbs: "",
  });
  const [busy, setBusy] = useState(false);

  const ageValue = parseAmount(age);
  const heightValue = parseAmount(height);
  const weightValue = parseAmount(weight);

  const problems = [
    ageValue === null || ageValue < 12 || ageValue > 100 || !Number.isInteger(ageValue) ? "возраст 12–100" : null,
    heightValue === null || heightValue < 100 || heightValue > 250 ? "рост 100–250 см" : null,
    weightValue === null || weightValue < 20 || weightValue > 400 ? "вес 20–400 кг" : null,
  ].filter(Boolean);

  const data: Anthropometry | null =
    problems.length === 0
      ? { sex, age: ageValue!, height_cm: heightValue!, activity, goal }
      : null;
  const result = data ? calculateNorm(data, weightValue!) : null;

  const startCustom = (checked: boolean) => {
    setCustom(checked);

    if (checked) {
      const base = profile?.targets ?? result;
      if (base) {
        setTargets({
          kcal: amountText(base.kcal),
          protein: amountText(base.protein),
          fat: amountText(base.fat),
          carbs: amountText(base.carbs),
        });
      }
    }
  };

  const customTargets: Macros | null = custom
    ? (() => {
        const values = {
          kcal: parseAmount(targets.kcal),
          protein: parseAmount(targets.protein),
          fat: parseAmount(targets.fat),
          carbs: parseAmount(targets.carbs),
        };
        return Object.values(values).every((value) => value !== null) ? (values as Macros) : null;
      })()
    : null;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!data || weightValue === null || (custom && !customTargets)) return;
    setBusy(true);

    try {
      // Новый вес попадает в журнал веса — из него считается норма
      if (journalWeight === null || Math.abs(journalWeight - weightValue) >= 0.05) {
        await bodyWeightApi.add(weightValue);
        if (user) setUser({ ...user, body_weight: weightValue });
      }

      const saved = await nutrition.saveProfile({ ...data, targets: custom ? customTargets : null });
      toast.success("Норма сохранена");
      onSaved(saved);
    } catch (error) {
      toast.error(error);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="block" aria-labelledby="calc-title">
      <h2 className="block-title" id="calc-title">
        {profile ? "Пересчитать норму" : "Рассчитать норму"}
      </h2>
      <form className="panel form norm-form" onSubmit={submit}>
        {!profile && (
          <p className="muted small">
            Калории и БЖУ на день по полу, возрасту, росту, весу и активности (формула Миффлина —
            Сан Жеора).
          </p>
        )}

        <ChoiceGrid
          label="Пол"
          value={sex}
          options={[
            { value: "male", label: "Мужской" },
            { value: "female", label: "Женский" },
          ]}
          onChange={setSex}
        />

        <div className="form-row form-row-3">
          <Field label="Возраст">
            <input inputMode="numeric" placeholder="30" value={age} onChange={(event) => setAge(event.target.value)} />
          </Field>
          <Field label="Рост, см">
            <input inputMode="decimal" placeholder="178" value={height} onChange={(event) => setHeight(event.target.value)} />
          </Field>
          <Field label="Вес, кг">
            <input inputMode="decimal" placeholder="75" value={weight} onChange={(event) => setWeight(event.target.value)} />
          </Field>
        </div>
        <p className="field-hint norm-weight-hint">
          {journalWeight === null
            ? "Вес запишется в журнал веса тела."
            : weightValue !== null && Math.abs(journalWeight - weightValue) >= 0.05
              ? `В журнале ${formatNumber(journalWeight)} кг — новый вес запишем за сегодня.`
              : "Вес — из журнала веса тела."}
        </p>

        <Field label="Активность">
          <select value={activity} onChange={(event) => setActivity(event.target.value as Activity)}>
            {ACTIVITIES.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </Field>
        <p className="field-hint norm-goal-hint">
          {ACTIVITIES.find((item) => item.value === activity)?.hint}
        </p>

        <ChoiceGrid
          label="Цель"
          value={goal}
          options={GOALS.map((item) => ({ value: item.value, label: item.label }))}
          onChange={setGoal}
        />
        <p className="field-hint norm-goal-hint">{GOALS.find((item) => item.value === goal)?.hint}</p>

        {result ? (
          <div className="norm-result" aria-live="polite">
            <dl className="norm-figures">
              <div>
                <dt>Ккал</dt>
                <dd>{formatNumber(result.kcal)}</dd>
              </div>
              {MACROS.map((macro) => (
                <div key={macro.key}>
                  <dt>{macro.label}</dt>
                  <dd>
                    {formatNumber(result[macro.key])}
                    <small> г</small>
                  </dd>
                </div>
              ))}
            </dl>
            <p className="muted small">
              Основной обмен {formatNumber(result.bmr)} ккал · расход с активностью{" "}
              {formatNumber(result.tdee)} ккал
            </p>
          </div>
        ) : (
          <p className="muted small">Укажите {problems.join(", ")} — норма посчитается сразу.</p>
        )}

        <label className="toggle">
          <input type="checkbox" checked={custom} onChange={(event) => startCustom(event.target.checked)} />
          Задать свою норму (например, от тренера или диетолога)
        </label>

        {custom && (
          <div className="macro-inputs">
            {(["kcal", "protein", "fat", "carbs"] as (keyof Macros)[]).map((key) => (
              <Field key={key} label={key === "kcal" ? "Ккал" : `${MACROS.find((m) => m.key === key)?.label}, г`}>
                <input
                  inputMode="decimal"
                  value={targets[key]}
                  onChange={(event) => setTargets({ ...targets, [key]: event.target.value })}
                />
              </Field>
            ))}
          </div>
        )}

        <div className="modal-actions">
          {onCancel && <Button onClick={onCancel}>Отмена</Button>}
          <Button
            variant="primary"
            type="submit"
            icon="check"
            busy={busy}
            disabled={!data || (custom && !customTargets)}
          >
            Сохранить норму
          </Button>
        </div>
      </form>
      {!profile && (
        <p className="muted small norm-skip">
          <Icon name="food" size={16} /> Дневник ниже работает и без нормы.
        </p>
      )}
    </section>
  );
}
