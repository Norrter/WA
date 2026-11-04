// Тема оформления: тёмная, светлая или как в системе.
// Выбор хранится в браузере; до загрузки приложения тему ставит
// скрипт в index.html, чтобы страница не мигала.

import { useEffect, useState } from "react";

export type ThemeChoice = "dark" | "light" | "system";

const KEY = "gg-theme";
const media = () => window.matchMedia("(prefers-color-scheme: light)");

export function readTheme(): ThemeChoice {
  try {
    const value = localStorage.getItem(KEY);
    if (value === "dark" || value === "light" || value === "system") return value;
  } catch {
    // хранилище недоступно — берём системную
  }
  return "system";
}

function resolve(choice: ThemeChoice): "dark" | "light" {
  if (choice === "system") return media().matches ? "light" : "dark";
  return choice;
}

const listeners = new Set<(choice: ThemeChoice) => void>();

export function applyTheme(choice: ThemeChoice) {
  const theme = resolve(choice);
  document.documentElement.dataset.theme = theme;
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute("content", theme === "light" ? "#f3efea" : "#1b1c1e");
}

export function setTheme(choice: ThemeChoice) {
  try {
    localStorage.setItem(KEY, choice);
  } catch {
    // не сохранилось — тема всё равно сменится до перезагрузки
  }
  applyTheme(choice);
  listeners.forEach((listener) => listener(choice));
}

// Текущий выбор и функция смены; следит за системной темой
export function useTheme(): [ThemeChoice, (choice: ThemeChoice) => void, "dark" | "light"] {
  const [choice, setChoice] = useState<ThemeChoice>(readTheme);
  const [, rerender] = useState(0);

  useEffect(() => {
    listeners.add(setChoice);
    const query = media();
    const onSystem = () => {
      if (readTheme() === "system") {
        applyTheme("system");
        rerender((n) => n + 1);
      }
    };
    query.addEventListener("change", onSystem);
    return () => {
      listeners.delete(setChoice);
      query.removeEventListener("change", onSystem);
    };
  }, []);

  return [choice, setTheme, resolve(choice)];
}
