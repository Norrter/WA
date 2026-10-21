import { useEffect, useState, type ReactNode } from "react";

import type { Route } from "../lib/router";
import { useAuth } from "./Auth";
import { Icon, type IconName } from "./Icon";
import { Meander } from "./Meander";

interface NavItem {
  href: string;
  label: string;
  icon: IconName;
  match: Route["name"][];
}

const TODAY: NavItem = { href: "#/", label: "Сегодня", icon: "dumbbell", match: ["today", "workout"] };
const SCHEDULE: NavItem = { href: "#/schedule", label: "Расписание", icon: "month", match: ["schedule"] };
const PROGRAMS: NavItem = { href: "#/programs", label: "Программы", icon: "list", match: ["programs", "program"] };
const EXERCISES: NavItem = { href: "#/exercises", label: "Упражнения", icon: "dumbbell", match: ["exercises", "exercise"] };
const PROGRESS: NavItem = { href: "#/progress", label: "Прогресс", icon: "chart", match: ["progress"] };
const PROFILE: NavItem = { href: "#/profile", label: "Профиль", icon: "profile", match: ["profile"] };

// Раздел видят только тренеры
const COACH: NavItem = {
  href: "#/coach",
  label: "Клиенты",
  icon: "coach",
  match: ["coach", "coachUser", "coachWorkout"],
};

// Админ-панель — только администраторам
const ADMIN: NavItem = { href: "#/admin", label: "Админ-панель", icon: "admin", match: ["admin"] };

const NAV = [TODAY, SCHEDULE, PROGRAMS, EXERCISES, PROGRESS, PROFILE];

// Телефон: четыре раздела в нижней панели, остальное — в «Ещё»
const TABS = [TODAY, SCHEDULE, PROGRAMS, PROGRESS];

// Заголовок и кнопка «назад» в верхней панели телефона
function screenOf(route: Route): { title: string; back?: string } {
  switch (route.name) {
    case "today":
      return { title: "Сегодня" };
    case "workout":
      return { title: "Тренировка", back: "#/" };
    case "schedule":
      return { title: "Расписание" };
    case "programs":
      return { title: "Программы" };
    case "program":
      return { title: "Программа", back: "#/programs" };
    case "exercises":
      return { title: "Упражнения" };
    case "exercise":
      return { title: "Упражнение", back: "#/exercises" };
    case "progress":
      return { title: "Прогресс" };
    case "profile":
      return { title: "Профиль" };
    case "coach":
      return { title: "Клиенты" };
    case "coachUser":
      return { title: "Клиент", back: "#/coach" };
    case "coachWorkout":
      return { title: "Тренировка клиента", back: `#/coach/clients/${route.id}` };
    case "admin":
      return { title: "Админ-панель" };
    default:
      return { title: "Greek's Gym", back: "#/" };
  }
}

export function Layout({ route, children }: { route: Route; children: ReactNode }) {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  // Метка для стилей: внутри приложения (не на экране входа)
  useEffect(() => {
    document.body.classList.add("app-shell");
    return () => document.body.classList.remove("app-shell");
  }, []);

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

  const extra = [
    ...(user?.role === "coach" ? [COACH] : []),
    ...(user?.is_admin ? [ADMIN] : []),
  ];
  const nav = [
    ...NAV,
    ...extra.map((item) => ({ ...item, label: item === COACH ? "Тренер" : "Админ" })),
  ];
  // Всё, что не поместилось в нижнюю панель
  const more = [EXERCISES, PROFILE, ...extra];

  const isActive = (item: NavItem) => item.match.includes(route.name);
  const moreActive = more.some(isActive);
  const screen = screenOf(route);
  const initial = (user?.username ?? "?").trim().charAt(0).toUpperCase();

  const tab = (item: NavItem) => (
    <a
      key={item.href}
      href={item.href}
      className={`tab ${isActive(item) ? "active" : ""}`}
      aria-current={isActive(item) ? "page" : undefined}
    >
      <Icon name={item.icon} size={24} />
      <span>{item.label}</span>
    </a>
  );

  return (
    <div className="shell">
      {/* Компьютер: логотип и разделы в одну строку */}
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
      </header>

      {/* Телефон: меандр, затем «назад» или логотип — заголовок — аватар */}
      <header className="appbar">
        <Meander />
        <div className="appbar-row">
          {screen.back ? (
            <a className="round-button" href={screen.back} aria-label="Назад">
              <Icon name="left" size={20} strokeWidth={2} />
            </a>
          ) : (
            <a className="appbar-brand" href="#/" aria-label="Greek's Gym, на главную">
              ΓΓ
            </a>
          )}
          {screen.back && <span className="appbar-title">{screen.title}</span>}
          <a className="avatar" href="#/profile" aria-label="Профиль">
            {initial}
          </a>
        </div>
      </header>

      <main className="content">{children}</main>

      <nav className="tabbar" aria-label="Основное меню">
        {TABS.map(tab)}
        <button
          type="button"
          className={`tab ${moreActive || menuOpen ? "active" : ""}`}
          aria-expanded={menuOpen}
          aria-controls="more-menu"
          onClick={() => setMenuOpen((open) => !open)}
        >
          <Icon name="dots" size={24} />
          <span>Ещё</span>
        </button>
      </nav>

      {menuOpen && (
        <div className="sheet-backdrop" onClick={() => setMenuOpen(false)}>
          <div
            id="more-menu"
            className="sheet"
            role="dialog"
            aria-label="Ещё разделы"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="sheet-handle" aria-hidden="true" />
            <div className="sheet-user">
              <span className="avatar avatar-large" aria-hidden="true">{initial}</span>
              <span>
                <strong>{user?.username}</strong>
                <span className="sheet-user-email">{user?.email}</span>
              </span>
            </div>
            <nav aria-label="Ещё разделы">
              <ul className="sheet-list">
                {more.map((item) => (
                  <li key={item.href}>
                    <a
                      href={item.href}
                      className={`sheet-link ${isActive(item) ? "active" : ""}`}
                      aria-current={isActive(item) ? "page" : undefined}
                    >
                      <Icon name={item.icon} size={22} />
                      <span>{item.label}</span>
                      <Icon name="right" size={18} strokeWidth={2} />
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
            <button type="button" className="sheet-logout" onClick={logout}>
              <Icon name="logout" size={20} />
              Выйти
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
