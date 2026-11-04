// Добавление еды в дневник: из «моих продуктов» или вручную.
// Та же форма редактирует уже записанную еду.

import { useMemo, useState, type FormEvent } from "react";

import { nutrition } from "../api";
import type { Food, FoodEntry, FoodEntryInput, Macros, Meal } from "../api/types";
import { formatNumber } from "../lib/format";
import { amountText, MEALS, parseAmount, round1, scaleMacros } from "../lib/nutrition";
import { useAsync } from "../lib/useAsync";
import { Icon } from "./Icon";
import { useToast } from "./Toast";
import { Button, Field, IconButton, Modal } from "./ui";

type MacroKey = keyof Macros;

const MACRO_FIELDS: { key: MacroKey; label: string }[] = [
  { key: "kcal", label: "Ккал" },
  { key: "protein", label: "Белки, г" },
  { key: "fat", label: "Жиры, г" },
  { key: "carbs", label: "Углев., г" },
];

type MacroTexts = Record<MacroKey, string>;

const EMPTY: MacroTexts = { kcal: "", protein: "", fat: "", carbs: "" };

function toTexts(macros: Macros): MacroTexts {
  return {
    kcal: amountText(macros.kcal),
    protein: amountText(macros.protein),
    fat: amountText(macros.fat),
    carbs: amountText(macros.carbs),
  };
}

// Калории по БЖУ: 4 / 9 / 4 ккал на грамм
function kcalFromMacros(protein: number, fat: number, carbs: number): number {
  return Math.round(protein * 4 + fat * 9 + carbs * 4);
}

// Тексты полей → числа; пустые калории считаются по БЖУ
function readMacros(texts: MacroTexts): Macros | null {
  const protein = parseAmount(texts.protein) ?? 0;
  const fat = parseAmount(texts.fat) ?? 0;
  const carbs = parseAmount(texts.carbs) ?? 0;
  const kcal = parseAmount(texts.kcal) ?? kcalFromMacros(protein, fat, carbs);

  for (const key of ["kcal", "protein", "fat", "carbs"] as MacroKey[]) {
    if (texts[key].trim() !== "" && parseAmount(texts[key]) === null) return null;
  }

  return { kcal, protein, fat, carbs };
}

export function macrosLine(macros: Macros): string {
  return `Б ${formatNumber(round1(macros.protein))} · Ж ${formatNumber(round1(macros.fat))} · У ${formatNumber(round1(macros.carbs))}`;
}

function MealChoice({ value, onChange }: { value: Meal; onChange: (meal: Meal) => void }) {
  return (
    <div className="field">
      <span className="field-label">Приём пищи</span>
      <div className="choice-grid choice-grid-4" role="group" aria-label="Приём пищи">
        {MEALS.map((item) => (
          <button
            key={item.value}
            type="button"
            className={value === item.value ? "active" : ""}
            aria-pressed={value === item.value}
            onClick={() => onChange(item.value)}
          >
            {item.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function MacroInputs({
  texts,
  onChange,
  kcalPlaceholder,
}: {
  texts: MacroTexts;
  onChange: (texts: MacroTexts) => void;
  kcalPlaceholder?: string;
}) {
  return (
    <div className="macro-inputs">
      {MACRO_FIELDS.map((field) => (
        <Field key={field.key} label={field.label}>
          <input
            inputMode="decimal"
            placeholder={field.key === "kcal" ? kcalPlaceholder ?? "0" : "0"}
            value={texts[field.key]}
            onChange={(event) => onChange({ ...texts, [field.key]: event.target.value })}
          />
        </Field>
      ))}
    </div>
  );
}

function Preview({ macros, grams }: { macros: Macros; grams: number | null }) {
  return (
    <div className="food-preview" aria-live="polite">
      <span className="section-label">{grams ? `Порция ${formatNumber(grams)} г` : "Порция"}</span>
      <strong>{formatNumber(Math.round(macros.kcal))} ккал</strong>
      <span>{macrosLine(macros)}</span>
    </div>
  );
}

export function FoodDialog({
  date,
  meal: initialMeal,
  entry,
  onClose,
  onSaved,
}: {
  date: string;
  meal: Meal;
  entry?: FoodEntry;
  onClose: () => void;
  onSaved: () => void;
}) {
  if (entry) {
    return <EditEntry entry={entry} onClose={onClose} onSaved={onSaved} />;
  }

  return <AddEntry date={date} initialMeal={initialMeal} onClose={onClose} onSaved={onSaved} />;
}

function AddEntry({
  date,
  initialMeal,
  onClose,
  onSaved,
}: {
  date: string;
  initialMeal: Meal;
  onClose: () => void;
  onSaved: () => void;
}) {
  const toast = useToast();
  const foodsState = useAsync(() => nutrition.foods(), []);
  const [tab, setTab] = useState<"foods" | "manual" | null>(null);
  const [meal, setMeal] = useState<Meal>(initialMeal);
  const [busy, setBusy] = useState(false);

  // Мои продукты
  const [search, setSearch] = useState("");
  const [food, setFood] = useState<Food | null>(null);
  const [portion, setPortion] = useState("100");

  // Вручную
  const [name, setName] = useState("");
  const [grams, setGrams] = useState("");
  const [per100, setPer100] = useState(true);
  const [texts, setTexts] = useState<MacroTexts>(EMPTY);
  const [saveFood, setSaveFood] = useState(true);

  const foods = foodsState.data;
  // Пока список не загрузился — вкладка «вручную», если продуктов нет
  const shownTab = tab ?? (foods && foods.length > 0 ? "foods" : "manual");

  const found = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return (foods ?? []).filter((item) => item.name.toLowerCase().includes(needle));
  }, [foods, search]);

  const add = async (data: FoodEntryInput, message: string) => {
    setBusy(true);

    try {
      await nutrition.addEntry({ ...data, date, meal });
      toast.success(message);
      onSaved();
    } catch (error) {
      toast.error(error);
      setBusy(false);
    }
  };

  // --- Из моих продуктов
  const portionGrams = parseAmount(portion);
  const foodTotals = food && portionGrams ? scaleMacros(food, portionGrams / 100) : null;

  const submitFood = (event: FormEvent) => {
    event.preventDefault();
    if (!food || !foodTotals || !portionGrams) return;
    void add(
      { ...foodTotals, meal, name: food.name, grams: portionGrams, food_id: food.id },
      `${food.name} — в дневнике`,
    );
  };

  const removeFood = async (item: Food) => {
    try {
      await nutrition.removeFood(item.id);
      foodsState.setData((foods ?? []).filter((other) => other.id !== item.id));
      if (food?.id === item.id) setFood(null);
      toast.success(`«${item.name}» удалён из ваших продуктов`);
    } catch (error) {
      toast.error(error);
    }
  };

  // --- Вручную
  const manualGrams = parseAmount(grams);
  const entered = readMacros(texts);
  const manualTotals =
    entered && per100 ? (manualGrams ? scaleMacros(entered, manualGrams / 100) : null) : entered;
  const kcalHint = (() => {
    const protein = parseAmount(texts.protein) ?? 0;
    const fat = parseAmount(texts.fat) ?? 0;
    const carbs = parseAmount(texts.carbs) ?? 0;
    const value = kcalFromMacros(protein, fat, carbs);
    return value > 0 ? `≈ ${value}` : "0";
  })();
  const canSaveFood = !!manualGrams;
  const manualReady = name.trim() !== "" && manualTotals !== null;

  const submitManual = (event: FormEvent) => {
    event.preventDefault();
    if (!manualReady || !manualTotals) return;
    void add(
      {
        ...manualTotals,
        meal,
        name: name.trim(),
        grams: manualGrams || null,
        save_food: saveFood && canSaveFood,
      },
      saveFood && canSaveFood ? `${name.trim()} — в дневнике и в ваших продуктах` : `${name.trim()} — в дневнике`,
    );
  };

  return (
    <Modal title="Добавить еду" onClose={onClose}>
      <div className="food-dialog">
        <div className="tabs food-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={shownTab === "foods"}
            className={shownTab === "foods" ? "active" : ""}
            onClick={() => setTab("foods")}
          >
            Мои продукты{foods && foods.length > 0 ? ` · ${foods.length}` : ""}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={shownTab === "manual"}
            className={shownTab === "manual" ? "active" : ""}
            onClick={() => setTab("manual")}
          >
            Вручную
          </button>
        </div>

        {shownTab === "foods" ? (
          <form className="form" onSubmit={submitFood}>
            {foods && foods.length === 0 ? (
              <p className="muted small">
                Здесь появятся продукты, которые вы сохраните при ручном вводе — потом их можно
                добавлять в два касания.
              </p>
            ) : (
              <>
                <label className="search">
                  <Icon name="search" size={18} />
                  <input
                    type="search"
                    placeholder="Найти продукт"
                    aria-label="Найти продукт"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                  />
                </label>
                <ul className="food-list">
                  {found.map((item) => (
                    <li key={item.id} className={food?.id === item.id ? "is-selected" : ""}>
                      <button
                        type="button"
                        className="food-option"
                        aria-pressed={food?.id === item.id}
                        onClick={() => setFood(item)}
                      >
                        <span className="food-option-name">{item.name}</span>
                        <span className="food-option-meta">
                          100 г · {formatNumber(item.kcal)} ккал · {macrosLine(item)}
                        </span>
                      </button>
                      <IconButton
                        icon="trash"
                        label={`Удалить «${item.name}» из моих продуктов`}
                        onClick={() => void removeFood(item)}
                      />
                    </li>
                  ))}
                  {foods && found.length === 0 && <li className="food-list-empty">Ничего не найдено</li>}
                </ul>
              </>
            )}

            {food && (
              <>
                <Field label={`Сколько грамм — ${food.name}`}>
                  <input
                    inputMode="decimal"
                    value={portion}
                    autoFocus
                    onChange={(event) => setPortion(event.target.value)}
                  />
                </Field>
                <MealChoice value={meal} onChange={setMeal} />
                {foodTotals && <Preview macros={foodTotals} grams={portionGrams} />}
              </>
            )}

            <div className="modal-actions">
              <Button onClick={onClose}>Отмена</Button>
              <Button variant="primary" type="submit" busy={busy} disabled={!food || !foodTotals}>
                Добавить
              </Button>
            </div>
          </form>
        ) : (
          <form className="form" onSubmit={submitManual}>
            <div className="form-row food-name-row">
              <Field label="Что съели">
                <input
                  required
                  maxLength={150}
                  placeholder="Гречка варёная"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
              </Field>
              <Field label="Вес порции, г">
                <input
                  inputMode="decimal"
                  placeholder={per100 ? "обязательно" : "необязательно"}
                  value={grams}
                  onChange={(event) => setGrams(event.target.value)}
                />
              </Field>
            </div>

            <div className="field">
              <span className="field-label">КБЖУ указаны</span>
              <div className="choice-grid" role="group" aria-label="КБЖУ указаны">
                <button
                  type="button"
                  className={per100 ? "active" : ""}
                  aria-pressed={per100}
                  onClick={() => setPer100(true)}
                >
                  На 100 г
                </button>
                <button
                  type="button"
                  className={!per100 ? "active" : ""}
                  aria-pressed={!per100}
                  onClick={() => setPer100(false)}
                >
                  На всю порцию
                </button>
              </div>
            </div>

            <MacroInputs texts={texts} onChange={setTexts} kcalPlaceholder={kcalHint} />
            {entered === null && <p className="form-error">Числа — например, 12 или 12,5</p>}

            <MealChoice value={meal} onChange={setMeal} />

            {manualTotals && (per100 || manualTotals.kcal > 0) && (
              <Preview macros={manualTotals} grams={manualGrams} />
            )}

            <label className={`toggle ${canSaveFood ? "" : "is-disabled"}`}>
              <input
                type="checkbox"
                checked={saveFood && canSaveFood}
                disabled={!canSaveFood}
                onChange={(event) => setSaveFood(event.target.checked)}
              />
              {canSaveFood ? "Сохранить в мои продукты" : "Укажите вес порции, чтобы сохранить продукт"}
            </label>

            <div className="modal-actions">
              <Button onClick={onClose}>Отмена</Button>
              <Button variant="primary" type="submit" busy={busy} disabled={!manualReady}>
                Добавить
              </Button>
            </div>
          </form>
        )}
      </div>
    </Modal>
  );
}

function EditEntry({
  entry,
  onClose,
  onSaved,
}: {
  entry: FoodEntry;
  onClose: () => void;
  onSaved: () => void;
}) {
  const toast = useToast();
  const [meal, setMeal] = useState<Meal>(entry.meal);
  const [name, setName] = useState(entry.name);
  const [grams, setGrams] = useState(amountText(entry.grams));
  const [texts, setTexts] = useState<MacroTexts>(toTexts(entry));
  const [busy, setBusy] = useState<"save" | "remove" | null>(null);

  // Новый вес порции пересчитывает КБЖУ пропорционально
  const changeGrams = (text: string) => {
    const before = parseAmount(grams);
    const after = parseAmount(text);
    const current = readMacros(texts);

    if (before && after && current) {
      setTexts(toTexts(scaleMacros(current, after / before)));
    }

    setGrams(text);
  };

  const macros = readMacros(texts);
  const ready = name.trim() !== "" && macros !== null;

  const save = async (event: FormEvent) => {
    event.preventDefault();
    if (!macros || !ready) return;
    setBusy("save");

    try {
      await nutrition.updateEntry(entry.id, {
        ...macros,
        meal,
        name: name.trim(),
        grams: parseAmount(grams),
      });
      toast.success("Запись обновлена");
      onSaved();
    } catch (error) {
      toast.error(error);
      setBusy(null);
    }
  };

  const remove = async () => {
    setBusy("remove");

    try {
      await nutrition.removeEntry(entry.id);
      toast.success(`${entry.name} — удалено из дневника`);
      onSaved();
    } catch (error) {
      toast.error(error);
      setBusy(null);
    }
  };

  return (
    <Modal title="Запись в дневнике" onClose={onClose}>
      <form className="form food-dialog" onSubmit={save}>
        <div className="form-row food-name-row">
          <Field label="Что съели">
            <input required maxLength={150} value={name} onChange={(event) => setName(event.target.value)} />
          </Field>
          <Field label="Вес порции, г">
            <input inputMode="decimal" placeholder="—" value={grams} onChange={(event) => changeGrams(event.target.value)} />
          </Field>
        </div>
        <p className="muted small">КБЖУ на всю порцию. При смене веса они пересчитаются.</p>
        <MacroInputs texts={texts} onChange={setTexts} />
        {macros === null && <p className="form-error">Числа — например, 12 или 12,5</p>}
        <MealChoice value={meal} onChange={setMeal} />

        <div className="modal-actions food-edit-actions">
          <Button variant="ghost" icon="trash" busy={busy === "remove"} disabled={busy !== null} onClick={() => void remove()}>
            Удалить
          </Button>
          <Button onClick={onClose}>Отмена</Button>
          <Button variant="primary" type="submit" busy={busy === "save"} disabled={!ready || busy !== null}>
            Сохранить
          </Button>
        </div>
      </form>
    </Modal>
  );
}
