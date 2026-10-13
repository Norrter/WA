// Кабинет тренера: свои клиенты, добавление по email и показатели за период

import { useMemo, useState, type FormEvent } from "react";

import { coach } from "../api";
import type { CoachClientLink, ClientMetrics } from "../api/types";
import {
  FlagBadge,
  PeriodSwitch,
  formatPercent,
  periodStart,
  reasonsText,
  sinceText,
  workoutsDue,
} from "../components/Coaching";
import { Icon } from "../components/Icon";
import { useScene } from "../components/Scene";
import { useToast } from "../components/Toast";
import { Button, Empty, ErrorNote, Loading, PageHeader } from "../components/ui";
import { formatDay, today } from "../lib/dates";
import { useAsync } from "../lib/useAsync";

type Sort = "attention" | "activity" | "adherence" | "name";

const SORTS: { value: Sort; label: string }[] = [
  { value: "attention", label: "Сначала требующие внимания" },
  { value: "activity", label: "По последней тренировке" },
  { value: "adherence", label: "По выполнению плана" },
  { value: "name", label: "По имени" },
];

const FLAG_ORDER = { check: 0, progress: 1, on_track: 2 };

type ActiveClient = CoachClientLink & {
  client: NonNullable<CoachClientLink["client"]>;
  metrics: ClientMetrics;
};

function sortClients(clients: ActiveClient[], sort: Sort): ActiveClient[] {
  const byName = (a: ActiveClient, b: ActiveClient) =>
    a.client.username.localeCompare(b.client.username, "ru");
  const lastWorkout = (item: ActiveClient) => item.metrics.last_workout ?? "";
  const adherence = (item: ActiveClient) => item.metrics.adherence ?? -1;

  return [...clients].sort((a, b) => {
    switch (sort) {
      case "attention":
        return (
          FLAG_ORDER[a.metrics.flag] - FLAG_ORDER[b.metrics.flag]
          || lastWorkout(a).localeCompare(lastWorkout(b))
          || byName(a, b)
        );
      case "activity":
        return lastWorkout(b).localeCompare(lastWorkout(a)) || byName(a, b);
      case "adherence":
        return adherence(b) - adherence(a) || byName(a, b);
      default:
        return byName(a, b);
    }
  });
}

export function CoachPage() {
  useScene("colonnade");

  const toast = useToast();
  const [weeks, setWeeks] = useState(4);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<Sort>("attention");
  const now = today();
  const from = periodStart(weeks);

  const state = useAsync(() => coach.clients(from, now), [from, now]);
  const links = state.data ?? [];

  const active = links.filter(
    (link): link is ActiveClient => link.status === "active" && !!link.client && !!link.metrics,
  );
  // Добавлены по email, но ещё не зарегистрировались
  const waiting = links.filter((link) => link.status === "invited");
  const former = links.filter((link) => link.status === "ended");

  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase();
    const found = active.filter(
      (item) =>
        !needle
        || item.client.username.toLowerCase().includes(needle)
        || item.client.email.toLowerCase().includes(needle),
    );

    return sortClients(found, sort);
  }, [state.data, search, sort]);

  if (state.error) return <ErrorNote error={state.error} onRetry={() => void state.reload()} />;
  if (!state.data) return <Loading />;

  // Выполнение планов: все выполненные / все, что должно было пройти
  const done = active.reduce((sum, item) => sum + item.metrics.workouts_completed, 0);
  const due = active.reduce((sum, item) => sum + workoutsDue(item.metrics), 0);
  const needContact = active.filter((item) => item.metrics.flag === "check").length;

  const cancel = async (link: CoachClientLink) => {
    try {
      await coach.cancelInvitation(link.id);
      toast.success("Клиент убран из ожидания");
      void state.reload();
    } catch (error) {
      toast.error(error);
    }
  };

  return (
    <div className="page page-wide">
      <PageHeader
        eyebrow="Кабинет тренера"
        title="Клиенты"
        subtitle={`Показатели с ${formatDay(from)} по сегодня`}
        actions={<PeriodSwitch weeks={weeks} onChange={setWeeks} />}
      />

      <div className={state.loading ? "is-refreshing" : ""}>
        <dl className="figures">
          <div>
            <dt>Активные клиенты</dt>
            <dd>{active.length}</dd>
          </div>
          <div>
            <dt>Выполнение планов</dt>
            <dd>{formatPercent(due ? done / due : null)}</dd>
          </div>
          <div>
            <dt>Тренировки проведены</dt>
            <dd>{done}</dd>
          </div>
          <div className={needContact ? "figure-alert" : ""}>
            <dt>Нужен контакт</dt>
            <dd>{needContact}</dd>
          </div>
        </dl>

        <AddClientForm onAdded={() => void state.reload()} />

        <p className="coach-templates">
          Шаблоны для клиентов — это ваши программы.{" "}
          <a href="#/programs">Открыть программы</a>, а назначить — в карточке клиента.
        </p>

        <section className="block" aria-labelledby="clients-title">
          <h2 className="block-title" id="clients-title">Мои клиенты</h2>

          {active.length === 0 ? (
            <Empty title="Клиентов пока нет">
              <p className="muted">
                Добавьте человека по email — его тренировки и прогресс сразу появятся
                здесь.
              </p>
            </Empty>
          ) : (
            <>
              {active.length > 5 && (
                <div className="toolbar">
                  <div className="search">
                    <Icon name="search" size={18} />
                    <input
                      type="search"
                      placeholder="Имя или email"
                      aria-label="Найти клиента"
                      value={search}
                      onChange={(event) => setSearch(event.target.value)}
                    />
                  </div>
                  <select
                    className="coach-sort"
                    aria-label="Сортировка"
                    value={sort}
                    onChange={(event) => setSort(event.target.value as Sort)}
                  >
                    {SORTS.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {visible.length === 0 ? (
                <p className="muted">Никого не нашлось.</p>
              ) : (
                <ul className="clients">
                  {visible.map((item) => (
                    <ClientRow key={item.id} item={item} />
                  ))}
                </ul>
              )}
            </>
          )}
        </section>

        {waiting.length > 0 && (
          <section className="block" aria-labelledby="waiting-title">
            <h2 className="block-title" id="waiting-title">Ждут регистрации</h2>
            <ul className="rows">
              {waiting.map((link) => (
                <li key={link.id} className="row-item invite-row">
                  <span className="row-main">
                    {link.invited_email}
                    <span className="row-note">
                      добавлен {formatDay(link.created_at.slice(0, 10))} · станет клиентом сразу после
                      регистрации с этим email
                    </span>
                  </span>
                  <Button small variant="ghost" onClick={() => void cancel(link)}>
                    Убрать
                  </Button>
                </li>
              ))}
            </ul>
          </section>
        )}

        {former.length > 0 && (
          <section className="block" aria-labelledby="former-title">
            <h2 className="block-title" id="former-title">Завершённое сотрудничество</h2>
            <ul className="rows">
              {former.map((link) => (
                <li key={link.id} className="row-item">
                  <span className="row-main">
                    {link.client?.username ?? link.invited_email}
                    <span className="row-note">
                      {link.ended_at && `завершено ${formatDay(link.ended_at.slice(0, 10))}`}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </div>
  );
}

function ClientRow({ item }: { item: ActiveClient }) {
  const { metrics } = item;
  const reasons = reasonsText(metrics);

  return (
    <li>
      <a className={`client-row flag-row-${metrics.flag}`} href={`#/coach/clients/${item.client.id}`}>
        <span className="client-main">
          <span className="client-name">{item.client.username}</span>
          <span className="client-meta">
            Последняя тренировка: {sinceText(metrics.days_since_last_workout)}
            {reasons && <span className="client-reasons"> · {reasons}</span>}
          </span>
        </span>
        <span className="client-figure">
          <span className="client-percent">{formatPercent(metrics.adherence)}</span>
          <span className="client-percent-label">выполнение</span>
        </span>
        <FlagBadge metrics={metrics} />
      </a>
    </li>
  );
}

function AddClientForm({ onAdded }: { onAdded: () => void }) {
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);

    try {
      const link = await coach.invite(email);
      setEmail("");
      toast.success(
        link.client
          ? `${link.client.username} теперь ваш клиент`
          : "Такого пользователя ещё нет. Человек станет вашим клиентом, как только зарегистрируется с этим email.",
      );
      onAdded();
    } catch (error) {
      toast.error(error);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="block invite" aria-labelledby="invite-title">
      <h2 className="block-title" id="invite-title">Добавить клиента</h2>
      <form className="invite-form" onSubmit={submit}>
        <input
          type="email"
          required
          placeholder="email клиента"
          aria-label="Email клиента"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <Button variant="primary" type="submit" icon="plus" busy={busy}>
          Добавить
        </Button>
      </form>
      <p className="field-hint">
        Клиент добавляется сразу, без подтверждения: вы увидите его тренировки и прогресс и сможете
        назначать программы. У клиента может быть только один тренер.
      </p>
    </section>
  );
}
