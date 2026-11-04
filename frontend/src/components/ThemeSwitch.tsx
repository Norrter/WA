// Переключатели темы: три варианта для профиля и меню «Ещё»
// и круглая кнопка солнце/луна для верхних панелей.

import { useTheme, type ThemeChoice } from "../lib/theme";
import { Icon } from "./Icon";

const OPTIONS: { value: ThemeChoice; label: string }[] = [
  { value: "dark", label: "Тёмная" },
  { value: "light", label: "Светлая" },
  { value: "system", label: "Как в системе" },
];

export function ThemeChoices({ label = "Тема" }: { label?: string }) {
  const [choice, setChoice] = useTheme();

  return (
    <div className="theme-choices" role="radiogroup" aria-label={label}>
      {OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={choice === option.value}
          className={choice === option.value ? "active" : ""}
          onClick={() => setChoice(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

export function ThemeToggle({ className = "" }: { className?: string }) {
  const [, setChoice, theme] = useTheme();
  const next = theme === "dark" ? "light" : "dark";

  return (
    <button
      type="button"
      className={`theme-toggle ${className}`}
      aria-label={next === "light" ? "Включить светлую тему" : "Включить тёмную тему"}
      title={next === "light" ? "Светлая тема" : "Тёмная тема"}
      onClick={() => setChoice(next)}
    >
      <Icon name={theme === "dark" ? "sun" : "moon"} size={20} />
    </button>
  );
}
