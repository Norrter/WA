import type { ReactNode } from "react";

import type { Route } from "../lib/router";
import { useAuth } from "./Auth";
import { Icon, type IconName } from "./Icon";

const NAV: { href: string; label: string; icon: IconName; match: Route["name"][] }[] = [
  { href: "#/", label: "Сегодня", icon: "today", match: ["today", "workout"] },
  { href: "#/schedule", label: "Расписание", icon: "calendar", match: ["schedule"] },
  { href: "#/programs", label: "Программы", icon: "programs", match: ["programs", "program"] },
  { href: "#/exercises", label: "Упражнения", icon: "exercises", match: ["exercises", "exercise"] },
  { href: "#/progress", label: "Прогресс", icon: "progress", match: ["progress"] },
  { href: "#/profile", label: "Профиль", icon: "profile", match: ["profile"] },
];

export function Layout({ route, children }: { route: Route; children: ReactNode }) {
  const { user } = useAuth();

  return (
    <div className="shell">
      <aside className="sidebar">
        <a className="wordmark" href="#/">
          <span className="wordmark-plates" aria-hidden="true">
            <i className="plate-dot red" />
            <i className="plate-dot blue" />
            <i className="plate-dot yellow" />
          </span>
          Журнал
        </a>

        <nav className="nav" aria-label="Разделы">
          {NAV.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className={`nav-link ${item.match.includes(route.name) ? "active" : ""}`}
              aria-current={item.match.includes(route.name) ? "page" : undefined}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
            </a>
          ))}
        </nav>

        <p className="sidebar-user">{user?.username}</p>
      </aside>

      <main className="content">{children}</main>
    </div>
  );
}
