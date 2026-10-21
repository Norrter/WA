// Базовые элементы интерфейса

import {
  useEffect,
  useState,
  type ButtonHTMLAttributes,
  type ReactNode,
} from "react";

import type { WorkoutStatus } from "../api/types";
import { today as todayISO } from "../lib/dates";
import { Icon, type IconName } from "./Icon";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  icon?: IconName;
  small?: boolean;
  busy?: boolean;
}

export function Button({
  variant = "secondary",
  icon,
  small,
  busy,
  children,
  className = "",
  disabled,
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`btn btn-${variant} ${small ? "btn-small" : ""} ${className}`}
      disabled={disabled || busy}
      {...rest}
    >
      {icon && <Icon name={icon} size={small ? 16 : 18} />}
      {children && <span>{busy ? "Подождите…" : children}</span>}
    </button>
  );
}

export function IconButton({
  icon,
  label,
  ...rest
}: Omit<ButtonProps, "children"> & { icon: IconName; label: string }) {
  return (
    <Button
      variant="ghost"
      small
      icon={icon}
      aria-label={label}
      title={label}
      className="btn-icon"
      {...rest}
    />
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

export function Modal({
  title,
  onClose,
  children,
  wide,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };

    document.addEventListener("keydown", onKey);
    document.body.classList.add("no-scroll");

    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.classList.remove("no-scroll");
    };
  }, [onClose]);

  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div
        className={`modal ${wide ? "modal-wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-head">
          <h2>{title}</h2>
          <IconButton icon="close" label="Закрыть" onClick={onClose} />
        </div>
        {children}
      </div>
    </div>
  );
}

// Диалог подтверждения: const [dialog, confirm] = useConfirm();
// if (await confirm("Удалить?", "Удалить")) { ... }; {dialog} — в разметке
export function useConfirm(): [
  ReactNode,
  (message: string, actionLabel: string) => Promise<boolean>,
] {
  const [request, setRequest] = useState<{
    message: string;
    actionLabel: string;
    resolve: (value: boolean) => void;
  } | null>(null);

  const ask = (message: string, actionLabel: string) =>
    new Promise<boolean>((resolve) => setRequest({ message, actionLabel, resolve }));

  const finish = (value: boolean) => {
    request?.resolve(value);
    setRequest(null);
  };

  const dialog = request && (
    <Modal title="Подтвердите действие" onClose={() => finish(false)}>
      <p className="modal-text">{request.message}</p>
      <div className="modal-actions">
        <Button onClick={() => finish(false)}>Отмена</Button>
        <Button variant="danger" onClick={() => finish(true)} autoFocus>
          {request.actionLabel}
        </Button>
      </div>
    </Modal>
  );

  return [dialog, ask];
}

export type DisplayStatus = WorkoutStatus | "unmarked";

const STATUS_LABELS: Record<DisplayStatus, string> = {
  planned: "В плане",
  completed: "Выполнена",
  skipped: "Пропуск",
  unmarked: "Не отмечена",
};

// Тренировка в плане, дата которой прошла, — «не отмечена»
export function displayStatus(status: WorkoutStatus, date?: string): DisplayStatus {
  if (status === "planned" && date !== undefined && date < todayISO()) return "unmarked";
  return status;
}

export function statusLabel(status: DisplayStatus): string {
  return STATUS_LABELS[status];
}

export function StatusPill({ status, date }: { status: WorkoutStatus; date?: string }) {
  const shown = displayStatus(status, date);
  return <span className={`status status-${shown}`}>{STATUS_LABELS[shown]}</span>;
}

export function Loading() {
  return (
    <div className="loading" role="status">
      <span className="loading-bar" />
      <span className="visually-hidden">Загрузка</span>
    </div>
  );
}

export function ErrorNote({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  return (
    <div className="error-note" role="alert">
      <p>{error.message}</p>
      {onRetry && <Button small onClick={onRetry}>Повторить</Button>}
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <p className="empty-title">{title}</p>
      {children}
    </div>
  );
}

// Поле числа с кнопками − и +
export function Stepper({
  label,
  value,
  onChange,
  step,
  min = 0,
  unit,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  step: number;
  min?: number;
  unit?: string;
}) {
  // В поле показываем русскую запятую: 82,5
  const show = (number: number) => String(number).replace(".", ",");
  const [text, setText] = useState(show(value));

  // Значение поменяли снаружи (например, после записи подхода)
  useEffect(() => {
    setText((current) =>
      Number(current.replace(",", ".")) === value ? current : show(value),
    );
  }, [value]);

  const change = (next: number) => {
    const rounded = Math.max(min, Math.round(next * 100) / 100);
    setText(show(rounded));
    onChange(rounded);
  };

  return (
    <div className="stepper">
      <span className="stepper-label">{label}</span>
      <div className="stepper-row">
        <button
          type="button"
          className="stepper-btn"
          aria-label={`${label}: меньше`}
          onClick={() => change(value - step)}
          disabled={value - step < min}
        >
          <Icon name="minus" />
        </button>
        <input
          className="stepper-input"
          inputMode="decimal"
          value={text}
          aria-label={label}
          onChange={(event) => {
            setText(event.target.value);
            const parsed = Number(event.target.value.replace(",", "."));
            if (event.target.value.trim() !== "" && Number.isFinite(parsed)) {
              onChange(Math.max(min, parsed));
            }
          }}
          onBlur={() => setText(show(value))}
        />
        {unit && <span className="stepper-unit">{unit}</span>}
        <button
          type="button"
          className="stepper-btn"
          aria-label={`${label}: больше`}
          onClick={() => change(value + step)}
        >
          <Icon name="plus" />
        </button>
      </div>
    </div>
  );
}

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  actions,
  back,
}: {
  // Короткая подпись над заголовком: контекст экрана
  eyebrow?: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  back?: { href: string; label: string };
}) {
  return (
    <header className="page-header">
      {back && (
        <a className="back-link" href={back.href}>
          <Icon name="left" size={16} />
          {back.label}
        </a>
      )}
      <div className="page-header-row">
        <div>
          {eyebrow && <p className="eyebrow">{eyebrow}</p>}
          <h1 className="page-title">{title}</h1>
          {subtitle && <p className="page-subtitle">{subtitle}</p>}
        </div>
        {actions && <div className="page-actions">{actions}</div>}
      </div>
    </header>
  );
}
