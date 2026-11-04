// Заявки с главной страницы: кто, на какой тариф, как связаться.
// Тренер отмечает, что взял заявку в работу, и оставляет себе заметку.

import { useState } from "react";

import { leads as leadsApi } from "../api";
import type { Lead, LeadStatus } from "../api/types";
import { Icon } from "../components/Icon";
import { useScene } from "../components/Scene";
import { useToast } from "../components/Toast";
import { Button, Empty, ErrorNote, IconButton, Loading, PageHeader, useConfirm } from "../components/ui";
import { formatDay, today, toISO } from "../lib/dates";
import { useAsync } from "../lib/useAsync";

export const LEAD_STATUSES: { value: LeadStatus; label: string }[] = [
  { value: "new", label: "Новые" },
  { value: "in_progress", label: "В работе" },
  { value: "done", label: "Стали клиентами" },
  { value: "rejected", label: "Отказ" },
];

const STATUS_SHORT: Record<LeadStatus, string> = {
  new: "Новая",
  in_progress: "В работе",
  done: "Клиент",
  rejected: "Отказ",
};

// Ссылка, чтобы написать или позвонить в одно касание
export function contactLink(contact: string): { href: string; label: string } | null {
  const value = contact.trim();
  const telegram = value.match(/^(?:@|(?:https?:\/\/)?t\.me\/)([A-Za-z0-9_]{4,32})$/);
  if (telegram) return { href: `https://t.me/${telegram[1]}`, label: "Telegram" };

  if (/^\S+@\S+\.\S+$/.test(value)) return { href: `mailto:${value}`, label: "Почта" };

  const digits = value.replace(/[^\d+]/g, "");
  if (digits.replace("+", "").length >= 10) return { href: `tel:${digits}`, label: "Позвонить" };

  return null;
}

function when(value: string): string {
  const date = new Date(value);
  const day = toISO(date);
  const time = date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  return `${day === today() ? "сегодня" : formatDay(day)}, ${time}`;
}

export function LeadsPage() {
  useScene("colonnade");

  const [filter, setFilter] = useState<LeadStatus | "all">("new");
  const state = useAsync(() => leadsApi.list(), []);

  if (state.error) return <ErrorNote error={state.error} onRetry={() => void state.reload()} />;
  if (!state.data) return <Loading />;

  const all = state.data;
  const shown = filter === "all" ? all : all.filter((lead) => lead.status === filter);
  const count = (status: LeadStatus) => all.filter((lead) => lead.status === status).length;

  const replace = (next: Lead) => state.setData(all.map((lead) => (lead.id === next.id ? next : lead)));
  const drop = (id: number) => state.setData(all.filter((lead) => lead.id !== id));

  return (
    <div className="page leads-page">
      <PageHeader
        back={{ href: "#/coach", label: "Клиенты" }}
        eyebrow="Кабинет тренера"
        title="Заявки"
        subtitle="С главной страницы сайта. Свяжитесь с человеком и отметьте, чем закончилось."
      />

      <div className="leads-filter" role="group" aria-label="Показать">
        {LEAD_STATUSES.map((item) => (
          <button
            key={item.value}
            type="button"
            className={filter === item.value ? "active" : ""}
            aria-pressed={filter === item.value}
            onClick={() => setFilter(item.value)}
          >
            {item.label}
            <span className="leads-filter-count">{count(item.value)}</span>
          </button>
        ))}
        <button
          type="button"
          className={filter === "all" ? "active" : ""}
          aria-pressed={filter === "all"}
          onClick={() => setFilter("all")}
        >
          Все
          <span className="leads-filter-count">{all.length}</span>
        </button>
      </div>

      {shown.length === 0 ? (
        <Empty title={filter === "new" ? "Новых заявок нет" : "Здесь пусто"}>
          {all.length === 0
            ? "Заявки появятся, когда гости оставят их на главной странице."
            : "Посмотрите другие вкладки."}
        </Empty>
      ) : (
        <ul className="leads-list">
          {shown.map((lead) => (
            <LeadCard key={lead.id} lead={lead} onChange={replace} onRemove={drop} />
          ))}
        </ul>
      )}

      <p className="muted small leads-hint">
        Когда человек станет клиентом, добавьте его email в разделе «Клиенты» — после регистрации он
        сразу появится у вас.
      </p>
    </div>
  );
}

function LeadCard({
  lead,
  onChange,
  onRemove,
}: {
  lead: Lead;
  onChange: (lead: Lead) => void;
  onRemove: (id: number) => void;
}) {
  const toast = useToast();
  const [confirmDialog, confirm] = useConfirm();
  const [note, setNote] = useState(lead.note ?? "");
  const [busy, setBusy] = useState<string | null>(null);
  const link = contactLink(lead.contact);
  const noteChanged = note.trim() !== (lead.note ?? "");

  const update = async (changes: { status?: LeadStatus; note?: string }, key: string, message: string) => {
    setBusy(key);

    try {
      onChange(await leadsApi.update(lead.id, changes));
      toast.success(message);
    } catch (error) {
      toast.error(error);
    } finally {
      setBusy(null);
    }
  };

  const remove = async () => {
    if (!(await confirm(`Удалить заявку от ${lead.name}?`, "Удалить"))) return;

    try {
      await leadsApi.remove(lead.id);
      onRemove(lead.id);
    } catch (error) {
      toast.error(error);
    }
  };

  return (
    <li className={`lead is-${lead.status}`}>
      <div className="lead-head">
        <div className="lead-who">
          <h3>{lead.name}</h3>
          <span className="muted small">{when(lead.created_at)}</span>
        </div>
        <span className={`lead-status is-${lead.status}`}>{STATUS_SHORT[lead.status]}</span>
      </div>

      <div className="lead-contact">
        <span className="lead-contact-value">{lead.contact}</span>
        {link && (
          <a className="btn btn-secondary btn-small" href={link.href} target="_blank" rel="noreferrer">
            <Icon name="send" size={16} />
            <span>{link.label}</span>
          </a>
        )}
      </div>

      <p className="lead-offer">
        <span className="section-label">Формат</span>
        {lead.offer_title ?? "Нужна консультация"}
      </p>
      {lead.goal && <p className="lead-goal">{lead.goal}</p>}

      <label className="lead-note">
        <span className="section-label">Заметка для себя</span>
        <textarea
          rows={2}
          maxLength={2000}
          placeholder="Например: написал в Telegram, созвон в четверг"
          value={note}
          onChange={(event) => setNote(event.target.value)}
        />
      </label>

      <div className="lead-actions">
        {noteChanged && (
          <Button small busy={busy === "note"} onClick={() => void update({ note: note.trim() }, "note", "Заметка сохранена")}>
            Сохранить заметку
          </Button>
        )}
        {lead.status !== "in_progress" && lead.status !== "done" && (
          <Button
            small
            variant="primary"
            busy={busy === "in_progress"}
            onClick={() => void update({ status: "in_progress" }, "in_progress", "Заявка в работе")}
          >
            Взять в работу
          </Button>
        )}
        {lead.status !== "done" && (
          <Button small icon="check" busy={busy === "done"} onClick={() => void update({ status: "done" }, "done", "Отмечено: стал клиентом")}>
            Стал клиентом
          </Button>
        )}
        {lead.status !== "rejected" && lead.status !== "done" && (
          <Button small variant="ghost" busy={busy === "rejected"} onClick={() => void update({ status: "rejected" }, "rejected", "Отмечено: отказ")}>
            Отказ
          </Button>
        )}
        {(lead.status === "done" || lead.status === "rejected") && (
          <Button small variant="ghost" busy={busy === "new"} onClick={() => void update({ status: "new" }, "new", "Заявка снова новая")}>
            Вернуть в новые
          </Button>
        )}
        <IconButton icon="trash" label="Удалить заявку" onClick={() => void remove()} />
      </div>
      {confirmDialog}
    </li>
  );
}
