// Вес тела: текущий вес, изменение за период, график и журнал записей.
// Человек записывает вес на экране «Прогресс», тренер видит его у клиента.

import { useState, type FormEvent } from "react";

import { bodyWeight as bodyWeightApi, coach } from "../api";
import type { BodyWeightEntry } from "../api/types";
import { formatDay, today } from "../lib/dates";
import { formatNumber } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { useAuth } from "./Auth";
import { TrendChart } from "./Charts";
import { useToast } from "./Toast";
import { Button, ErrorNote, IconButton, useConfirm } from "./ui";

// «−1,9 кг», «+0,4 кг», «0 кг»
function formatDelta(value: number): string {
  const rounded = Math.round(value * 10) / 10;
  if (rounded === 0) return "0 кг";
  return `${rounded > 0 ? "+" : "−"}${formatNumber(Math.abs(rounded))} кг`;
}

function BodyWeightPanel({
  entries,
  since,
  onAdd,
  onRemove,
}: {
  entries: BodyWeightEntry[];
  since: string;
  onAdd?: (weight: number, date: string) => Promise<void>;
  onRemove?: (entry: BodyWeightEntry) => Promise<void>;
}) {
  const [text, setText] = useState("");
  const [date, setDate] = useState(today());
  const [busy, setBusy] = useState(false);

  const latest = entries[entries.length - 1];
  const inPeriod = entries.filter((entry) => entry.date >= since);
  // Точка отсчёта: последняя запись до начала периода, иначе первая в периоде
  const before = [...entries].reverse().find((entry) => entry.date < since);
  const baseline = before ?? inPeriod[0];
  const change = latest && baseline && baseline.id !== latest.id ? latest.weight - baseline.weight : null;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const value = Number(text.replace(",", "."));
    if (!onAdd || !value) return;
    setBusy(true);

    try {
      await onAdd(value, date);
      setText("");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel body-weight">
      <div className="body-weight-head">
        <div>
          <span className="section-label">Сейчас</span>
          <p className="body-weight-current">
            {latest ? `${formatNumber(latest.weight)} кг` : "—"}
          </p>
          {latest && <span className="muted small">записано {formatDay(latest.date)}</span>}
        </div>
        {change !== null && (
          <div className="body-weight-change">
            <span className="section-label">За период</span>
            <p>{formatDelta(change)}</p>
            <span className="muted small">с {formatDay(baseline.date)}</span>
          </div>
        )}
      </div>

      {inPeriod.length >= 2 ? (
        <TrendChart
          points={inPeriod.map((entry) => ({ date: entry.date, value: entry.weight }))}
          unit="кг"
          fromZero={false}
          highlightBest={false}
        />
      ) : (
        <p className="muted small">
          {entries.length === 0
            ? onAdd
              ? "Записывайте вес раз в неделю или чаще — здесь появится график."
              : "Клиент ещё не записывал вес."
            : "Для графика нужно хотя бы две записи за период."}
        </p>
      )}

      {onAdd && (
        <form className="body-weight-form" onSubmit={submit}>
          <label className="panel-field">
            <span className="section-label">Вес, кг</span>
            <input
              inputMode="decimal"
              placeholder="например, 78,5"
              value={text}
              onChange={(event) => setText(event.target.value)}
            />
          </label>
          <label className="panel-field">
            <span className="section-label">Дата</span>
            <input
              type="date"
              max={today()}
              value={date}
              onChange={(event) => setDate(event.target.value || today())}
            />
          </label>
          <Button variant="primary" type="submit" busy={busy} disabled={!text.trim()}>
            Записать
          </Button>
        </form>
      )}

      {entries.length > 0 && (
        <ul className="body-weight-list">
          {[...entries]
            .reverse()
            .slice(0, 6)
            .map((entry, index, list) => {
              const previous = list[index + 1];

              return (
                <li key={entry.id}>
                  <span className="body-weight-date">{formatDay(entry.date)}</span>
                  <span className="body-weight-value">{formatNumber(entry.weight)} кг</span>
                  <span className="body-weight-delta">
                    {previous ? formatDelta(entry.weight - previous.weight) : ""}
                  </span>
                  {onRemove && (
                    <IconButton icon="trash" label="Удалить запись" onClick={() => void onRemove(entry)} />
                  )}
                </li>
              );
            })}
        </ul>
      )}
    </div>
  );
}

// Свой вес: запись, удаление, вес в профиле обновляется
export function BodyWeightSection({ since }: { since: string }) {
  const toast = useToast();
  const { user, setUser } = useAuth();
  const [confirmDialog, confirm] = useConfirm();
  const state = useAsync(() => bodyWeightApi.list(), []);

  const syncProfile = (entries: BodyWeightEntry[]) => {
    if (!user) return;
    const latest = entries[entries.length - 1];
    setUser({ ...user, body_weight: latest ? latest.weight : null });
  };

  const add = async (weight: number, date: string) => {
    try {
      await bodyWeightApi.add(weight, date);
      const entries = await bodyWeightApi.list();
      state.setData(entries);
      syncProfile(entries);
      toast.success("Вес записан");
    } catch (error) {
      toast.error(error);
    }
  };

  const remove = async (entry: BodyWeightEntry) => {
    if (!(await confirm(`Удалить запись ${formatNumber(entry.weight)} кг за ${formatDay(entry.date)}?`, "Удалить"))) {
      return;
    }

    try {
      await bodyWeightApi.remove(entry.id);
      const entries = (state.data ?? []).filter((item) => item.id !== entry.id);
      state.setData(entries);
      syncProfile(entries);
    } catch (error) {
      toast.error(error);
    }
  };

  return (
    <section className="block" aria-labelledby="body-weight-title">
      <h2 className="block-title" id="body-weight-title">Вес тела</h2>
      {state.error && <ErrorNote error={state.error} onRetry={() => void state.reload()} />}
      {state.data && (
        <BodyWeightPanel entries={state.data} since={since} onAdd={add} onRemove={remove} />
      )}
      {confirmDialog}
    </section>
  );
}

// Вес клиента у тренера — только просмотр
export function ClientBodyWeight({ clientId, since }: { clientId: number; since: string }) {
  const state = useAsync(() => coach.bodyWeight(clientId), [clientId]);

  return (
    <section className="block" aria-labelledby="client-weight-title">
      <h2 className="block-title" id="client-weight-title">Вес тела</h2>
      {state.error && <ErrorNote error={state.error} onRetry={() => void state.reload()} />}
      {state.data && <BodyWeightPanel entries={state.data} since={since} />}
    </section>
  );
}
