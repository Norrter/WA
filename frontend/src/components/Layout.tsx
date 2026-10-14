import { useEffect, useState, type ReactNode } from "react";

import type { Route } from "../lib/router";
import { useAuth } from "./Auth";
import { Icon, type IconName } from "./Icon";

interface NavItem {
  href: string;
  label: string;
  icon: IconName;
  match: Route["name"][];
}

const TODAY: NavItem = { href: "#/", label: "Сегодня", icon: "today", match: ["today", "workout"] };
const SCHEDULE: NavItem = { href: "#/schedule", label: "Расписание", icon: "calendar", match: ["schedule"] };
const PROGRAMS: NavItem = { href: "#/programs", label: "Программы", icon: "programs", match: ["programs", "program"] };
const EXERCISES: NavItem = { href: "#/exercises", label: "Упражнения", icon: "dumbbell", match: ["exercises", "exercise"] };
const PROGRESS: NavItem = { href: "#/progress", label: "Прогресс", icon: "progress", match: ["progress"] };
const PROFILE: NavItem = { href: "#/profile", label: "Профиль", icon: "profile", match: ["profile"] };

// Раздел видят только тренеры
const COACH: NavItem = {
  href: "#/coach",
  label: "Тренер",
  icon: "coach",
  match: ["coach", "coachUser", "coachWorkout"],
};

// Админ-панель — только администраторам
const ADMIN: NavItem = { href: "#/admin", label: "Админ", icon: "admin", match: ["admin"] };

const NAV = [TODAY, SCHEDULE, PROGRAMS, EXERCISES, PROGRESS, PROFILE];

// Телефон: четыре раздела в нижней панели, «Сегодня» — в центре
const TABS_LEFT = [SCHEDULE, PROGRAMS];
const TABS_RIGHT = [PROGRESS];

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
  const nav = [...NAV, ...extra];
  // Всё, что не поместилось в нижнюю панель
  const more = [EXERCISES, ...extra, PROFILE];

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
      <Icon name={item.icon} size={22} />
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

      {/* Телефон: назад — заголовок экрана — аватар */}
      <header className={`appbar ${scrolled ? "scrolled" : ""}`}>
        {screen.back ? (
          <a className="appbar-button" href={screen.back} aria-label="Назад">
            <Icon name="left" size={22} />
          </a>
        ) : (
          <a className="appbar-brand" href="#/" aria-label="Greek's Gym, на главную">
            GG
          </a>
        )}
        <span className="appbar-title">{screen.title}</span>
        <a className="avatar" href="#/profile" aria-label="Профиль">
          {initial}
        </a>
      </header>

      <main className="content">{children}</main>

      <nav className="tabbar" aria-label="Разделы">
        {TABS_LEFT.map(tab)}
        <a
          href={TODAY.href}
          className={`tab tab-center ${isActive(TODAY) ? "active" : ""}`}
          aria-current={isActive(TODAY) ? "page" : undefined}
        >
          <span className="tab-center-icon">
            <Icon name={TODAY.icon} size={24} />
          </span>
          <span>{TODAY.label}</span>
        </a>
        {TABS_RIGHT.map(tab)}
        <button
          type="button"
          className={`tab ${moreActive || menuOpen ? "active" : ""}`}
          aria-expanded={menuOpen}
          aria-controls="more-menu"
          onClick={() => setMenuOpen((open) => !open)}
        >
          <Icon name="menu" size={22} />
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
                      {item.label}
                      <Icon name="right" size={18} />
                    </a>
                  </li>
                ))}
                <li>
                  <button type="button" className="sheet-link sheet-logout" onClick={logout}>
                    <Icon name="logout" size={22} />
                    Выйти
                  </button>
                </li>
              </ul>
            </nav>
          </div>
        </div>
      )}
    </div>
  );
}
