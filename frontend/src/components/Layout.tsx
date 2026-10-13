import { useEffect, useState, type ReactNode } from "react";

import type { Route } from "../lib/router";
import { useAuth } from "./Auth";

const NAV: { href: string; label: string; match: Route["name"][] }[] = [
  { href: "#/", label: "Сегодня", match: ["today", "workout"] },
  { href: "#/schedule", label: "Расписание", match: ["schedule"] },
  { href: "#/programs", label: "Программы", match: ["programs", "program"] },
  { href: "#/exercises", label: "Упражнения", match: ["exercises", "exercise"] },
  { href: "#/progress", label: "Прогресс", match: ["progress"] },
  { href: "#/profile", label: "Профиль", match: ["profile"] },
];

// Админ-панель — только администраторам
const ADMIN_NAV = { href: "#/admin", label: "Админ", match: ["admin"] as Route["name"][] };

// Раздел видят только тренеры
const COACH_NAV = { href: "#/coach", label: "Тренер", match: ["coach", "coachUser"] as Route["name"][] };

export function Layout({ route, children }: { route: Route; children: ReactNode }) {
  const { user } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // При переходе на другой экран меню закрывается
  useEffect(() => setMenuOpen(false), [route]);

  useEffect(() => {
    if (!menuOpen) return;

    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };

    document.addEventListener("keydown", onKey);
    document.body.classList.add("no-scroll");

    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.classList.remove("no-scroll");
    };
  }, [menuOpen]);

  const nav = [
    ...NAV,
    ...(user?.role === "coach" ? [COACH_NAV] : []),
    ...(user?.is_admin ? [ADMIN_NAV] : []),
  ];
  const isActive = (item: (typeof NAV)[number]) => item.match.includes(route.name);

  return (
    <div className="shell">
      <header className={`topbar ${scrolled ? "scrolled" : ""}`}>
        <a className="brand" href="#/">Greek's Gym</a>

        <nav className="topnav" aria-label="Разделы">
          {nav.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className={`topnav-link ${isActive(item) ? "active" : ""}`}
              aria-current={isActive(item) ? "page" : undefined}
            >
              {item.label}
            </a>
          ))}
        </nav>

        <button
          type="button"
          className="menu-toggle"
          aria-expanded={menuOpen}
          aria-controls="mobile-menu"
          onClick={() => setMenuOpen((open) => !open)}
        >
          <span className="menu-toggle-lines" aria-hidden="true" />
          {menuOpen ? "Закрыть" : "Меню"}
        </button>
      </header>

      <div
        id="mobile-menu"
        className={`menu ${menuOpen ? "open" : ""}`}
        hidden={!menuOpen}
      >
        <nav aria-label="Разделы">
          <ol className="menu-list">
            {nav.map((item, index) => (
              <li key={item.href} style={{ animationDelay: `${index * 50}ms` }}>
                <a
                  href={item.href}
                  className={`menu-link ${isActive(item) ? "active" : ""}`}
                  aria-current={isActive(item) ? "page" : undefined}
                >
                  {item.label}
                </a>
              </li>
            ))}
          </ol>
        </nav>
        <p className="menu-user">{user?.username}</p>
      </div>

      <main className="content">{children}</main>
    </div>
  );
}
