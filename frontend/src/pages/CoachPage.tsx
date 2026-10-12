// Кабинет тренера: все пользователи и их активность за период

import { useMemo, useState } from "react";

import { coach } from "../api";
import type { CoachUser } from "../api/types";
import { Icon } from "../components/Icon";
import { useScene } from "../components/Scene";
import { Empty, ErrorNote, Loading, PageHeader } from "../components/ui";
import { addDays, formatDay, startOfWeek, today } from "../lib/dates";
import { formatNumber, plural } from "../lib/format";
import { navigate } from "../lib/router";
import { useAsync } from "../lib/useAsync";

export const COACH_PERIODS = [4, 12, 26];

// Две недели без тренировок — атлет «затих», строка приглушена
const QUIET_AFTER_DAYS = 14;

type Sort = "activity" | "volume" | "name";

const SORTS: { value: Sort; label: string }[] = [
  { value: "activity", label: "По последней тренировке" },
  { value: "volume", label: "По объёму" },
  { value: "name", label: "По имени" },
];

// Начало периода: понедельник weeks недель назад
export function periodStart(weeks: number): string {
  return addDays(startOfWeek(today()), -(weeks - 1) * 7);
}

export function PeriodSwitch({
  weeks,
  onChange,
}: {
  weeks: number;
  onChange: (weeks: number) => void;
}) {
  return (
    <div className="segmented" role="group" aria-label="Период">
      {COACH_PERIODS.map((value) => (
        <button
          key={value}
          type="button"
          className={weeks === value ? "active" : ""}
          aria-pressed={weeks === value}
          onClick={() => onChange(value)}
        >
          {value} {plural(value, "неделя", "недели", "недель")}
        </button>
      ))}
    </div>
  );
}

function sortUsers(users: CoachUser[], sort: Sort): CoachUser[] {
  const byName = (a: CoachUser, b: CoachUser) => a.username.localeCompare(b.username, "ru");

  return [...users].sort((a, b) => {
    if (sort === "volume") return b.total_volume - a.total_volume || byName(a, b);
    if (sort === "activity") {
      return (b.last_workout ?? "").localeCompare(a.last_workout ?? "") || byName(a, b);
    }
    return byName(a, b);
  });
}

export function CoachPage() {
  useScene("colonnade");

  const [weeks, setWeeks] = useState(4);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<Sort>("activity");
  const now = today();
  const from = periodStart(weeks);

  const state = useAsync(() => coach.users(from, now), [from, now]);

  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase();
    const users = (state.data ?? []).filter(
      (user) =>
        !needle
        || user.username.toLowerCase().includes(needle)
        || user.email.toLowerCase().includes(needle),
    );

    return sortUsers(users, sort);
  }, [state.data, search, sort]);

  if (state.error) return <ErrorNote error={state.error} onRetry={() => void state.reload()} />;
  if (!state.data) return <Loading />;

  const users = state.data;
  const active = users.filter((user) => user.workouts_completed > 0).length;
  const workouts = users.reduce((sum, user) => sum + user.workouts_completed, 0);
  const volume = users.reduce((sum, user) => sum + user.total_volume, 0);
  const quietSince = addDays(now, -QUIET_AFTER_DAYS);

  return (
    <div className="page page-wide">
      <PageHeader
        eyebrow="Кабинет тренера"
        title="Атлеты"
        subtitle={`Статистика всех пользователей с ${formatDay(from)} по сегодня.`}
        actions={<PeriodSwitch weeks={weeks} onChange={setWeeks} />}
      />

      <div className={state.loading ? "is-refreshing" : ""}>
        <dl className="figures">
          <div>
            <dt>Атлетов</dt>
            <dd>{users.length}</dd>
          </div>
          <div>
            <dt>Тренировались</dt>
            <dd>
              {active}
              <small> из {users.length}</small>
            </dd>
          </div>
          <div>
            <dt>Тренировок</dt>
            <dd>{workouts}</dd>
          </div>
          <div>
            <dt>Поднято</dt>
            <dd>{formatNumber(volume)} кг</dd>
          </div>
        </dl>

        <section className="block" aria-labelledby="athletes-title">
          <h2 className="block-title" id="athletes-title">Все атлеты</h2>

          <div className="toolbar">
            <div className="search">
              <Icon name="search" size={18} />
              <input
                type="search"
                placeholder="Имя или email"
                aria-label="Найти атлета"
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

          {visible.length === 0 ? (
            <Empty title="Никого не нашлось">
              <p className="muted">Проверьте имя или email.</p>
            </Empty>
          ) : (
            <table className="records athletes">
              <thead>
                <tr>
                  <th>Атлет</th>
                  <th>Тренировок</th>
                  <th className="hide-mobile">Подходов</th>
                  <th>Объём, кг</th>
                  <th className="hide-tablet">Последняя</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((user) => {
                  const quiet = !user.last_workout || user.last_workout < quietSince;

                  return (
                    <tr
                      key={user.id}
                      className={`selectable ${quiet ? "is-quiet" : ""}`}
                      onClick={() => navigate(`/coach/users/${user.id}`)}
                    >
                      <td>
                        <a
                          className="athlete-link"
                          href={`#/coach/users/${user.id}`}
                          onClick={(event) => event.stopPropagation()}
                        >
                          {user.username}
                        </a>
                        {user.role === "coach" && <span className="tag">тренер</span>}
                        <span className="athlete-email">{user.email}</span>
                      </td>
                      <td className="num">
                        {user.workouts_completed}
                        {user.workouts_skipped > 0 && (
                          <small className="athlete-skipped" title="Пропущено">
                            −{user.workouts_skipped}
                          </small>
                        )}
                      </td>
                      <td className="num hide-mobile">{user.total_sets}</td>
                      <td className="num">{formatNumber(user.total_volume)}</td>
                      <td className="hide-tablet muted">
                        {user.last_workout ? formatDay(user.last_workout) : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </section>
      </div>
    </div>
  );
}
