// Админ-панель: обзор и любые данные любой таблицы.
// Таблицы и поля приходят с сервера, форма строится по ним.

import { useEffect, useState, type FormEvent } from "react";

import { admin } from "../api";
import type { AdminColumn, AdminRow, AdminTable } from "../api/types";
import { Icon } from "../components/Icon";
import { useScene } from "../components/Scene";
import { useToast } from "../components/Toast";
import {
  Button,
  Empty,
  ErrorNote,
  Loading,
  Modal,
  PageHeader,
  useConfirm,
} from "../components/ui";
import { formatDay } from "../lib/dates";
import { formatNumber } from "../lib/format";
import { navigate } from "../lib/router";
import { useAsync } from "../lib/useAsync";

const PAGE = 50;

// Подписи полей; остальные показываются как есть
const LABELS: Record<string, string> = {
  id: "ID",
  username: "Имя",
  email: "Email",
  role: "Роль",
  password: "Пароль",
  name: "Название",
  description: "Описание",
  muscle_group: "Группа мышц",
  equipment: "Оборудование",
  created_by_user_id: "Автор (пользователь)",
  user_id: "Пользователь",
  assigned_by_coach_id: "Назначил тренер",
  source_program_id: "Копия программы",
  program_id: "Программа",
  program_day_id: "День программы",
  exercise_id: "Упражнение",
  program_exercise_id: "Упражнение в плане",
  order_index: "Порядок",
  sets: "Подходов",
  target_reps: "Повторы",
  target_reps_max: "Повторы до",
  target_weight: "Вес, кг",
  rest_seconds: "Отдых, сек",
  notes: "Заметки",
  scheduled_date: "Дата",
  status: "Статус",
  program_name: "Название программы",
  day_name: "Название дня",
  wellbeing: "Самочувствие",
  difficulty: "Сложность",
  feedback_comment: "Комментарий",
  feedback_at: "Оценка оставлена",
  scheduled_workout_id: "Тренировка",
  set_number: "Номер подхода",
  weight: "Вес",
  reps: "Повторы",
  completed: "Выполнен",
  coach_id: "Тренер",
  client_id: "Клиент",
  invited_email: "Email клиента",
  responded_at: "Ответ",
  ended_at: "Завершено",
  text: "Текст",
  created_at: "Создано",
  updated_at: "Изменено",
};

const label = (name: string) => LABELS[name] ?? name;

function display(column: AdminColumn | undefined, value: AdminRow[string]): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "да" : "нет";
  if (column?.kind === "date") return formatDay(String(value));
  if (column?.kind === "datetime") {
    const text = String(value);
    return `${formatDay(text.slice(0, 10))}, ${text.slice(11, 16)}`;
  }
  if (typeof value === "number") return formatNumber(value);

  const text = String(value);
  return text.length > 80 ? `${text.slice(0, 80)}…` : text;
}

type Filter = { field: string; value: string | number; label: string };

export function AdminPage({ table: tableName }: { table: string | null }) {
  useScene("colonnade");

  const meta = useAsync(() => Promise.all([admin.tables(), admin.stats()]), []);

  if (meta.error) return <ErrorNote error={meta.error} onRetry={() => void meta.reload()} />;
  if (!meta.data) return <Loading />;

  const [tables, stats] = meta.data;
  const current = tables.find((table) => table.name === tableName) ?? tables[0];

  return (
    <div className="page page-wide">
      <PageHeader
        eyebrow="Администратор"
        title="Админ-панель"
        subtitle="Все данные сайта. Изменения сразу видят пользователи — будьте внимательны."
      />

      <dl className="figures">
        <div>
          <dt>Пользователей</dt>
          <dd>{stats.counts.users ?? 0}</dd>
        </div>
        <div>
          <dt>Новых за неделю</dt>
          <dd>{stats.new_users_week}</dd>
        </div>
        <div>
          <dt>Тренировок за неделю</dt>
          <dd>{stats.workouts_week}</dd>
        </div>
        <div>
          <dt>Активных за неделю</dt>
          <dd>{stats.active_users_week}</dd>
        </div>
      </dl>

      <nav className="admin-tables" aria-label="Таблицы">
        {tables.map((table) => (
          <a
            key={table.name}
            href={`#/admin/${table.name}`}
            className={`admin-table-link ${table.name === current.name ? "active" : ""}`}
            aria-current={table.name === current.name ? "page" : undefined}
          >
            {table.label}
            <span className="admin-count">{stats.counts[table.name] ?? table.count}</span>
          </a>
        ))}
      </nav>

      <TableView
        key={current.name}
        table={current}
        tables={tables}
        onChanged={() => void meta.reload()}
      />
    </div>
  );
}

function TableView({
  table,
  tables,
  onChanged,
}: {
  table: AdminTable;
  tables: AdminTable[];
  onChanged: () => void;
}) {
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [filter, setFilter] = useState<Filter | null>(() => readPendingFilter(table.name));
  const [editing, setEditing] = useState<AdminRow | "new" | null>(null);

  // Поиск — после паузы в наборе
  useEffect(() => {
    const timer = setTimeout(() => {
      setQuery(search.trim());
      setOffset(0);
    }, 350);
    return () => clearTimeout(timer);
  }, [search]);

  const rows = useAsync(
    () =>
      admin.rows(table.name, {
        q: query || undefined,
        field: filter?.field,
        value: filter?.value,
        limit: PAGE,
        offset,
      }),
    [table.name, query, filter?.field, filter?.value, offset],
  );

  const columns = new Map(table.columns.map((column) => [column.name, column]));

  const refresh = () => {
    void rows.reload();
    onChanged();
  };

  return (
    <section className="block" aria-labelledby="admin-table-title">
      <div className="block-head">
        <h2 className="block-title" id="admin-table-title">{table.label}</h2>
        <Button small variant="primary" icon="plus" onClick={() => setEditing("new")}>
          Добавить
        </Button>
      </div>

      <div className="toolbar">
        <div className="search">
          <Icon name="search" size={18} />
          <input
            type="search"
            placeholder={table.searchable ? "Поиск или ID" : "ID"}
            aria-label="Поиск"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        {filter && (
          <button type="button" className="admin-filter" onClick={() => setFilter(null)}>
            {filter.label}
            <Icon name="close" size={14} />
          </button>
        )}
      </div>

      {rows.error && <ErrorNote error={rows.error} onRetry={() => void rows.reload()} />}
      {!rows.data && !rows.error && <Loading />}

      {rows.data && (
        <div className={rows.loading ? "is-refreshing" : ""}>
          {rows.data.rows.length === 0 ? (
            <Empty title="Записей нет">
              <p className="muted">Попробуйте изменить поиск или сбросить фильтр.</p>
            </Empty>
          ) : (
            <table className="records stack admin-grid">
              <thead>
                <tr>
                  {table.list_columns.map((name) => (
                    <th key={name}>{label(name)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.data.rows.map((row) => (
                  <tr key={String(row.id)} className="selectable" onClick={() => setEditing(row)}>
                    {table.list_columns.map((name, index) => (
                      <td key={name} data-label={index === 0 ? undefined : label(name)}>
                        {index === 0 ? (
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              setEditing(row);
                            }}
                          >
                            #{String(row[name])}
                          </button>
                        ) : (
                          display(columns.get(name), row[name])
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <div className="admin-pager">
            <span className="muted">
              {rows.data.total === 0
                ? "0 записей"
                : `${offset + 1}–${Math.min(offset + PAGE, rows.data.total)} из ${rows.data.total}`}
            </span>
            <Button small disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>
              Назад
            </Button>
            <Button
              small
              disabled={offset + PAGE >= rows.data.total}
              onClick={() => setOffset(offset + PAGE)}
            >
              Далее
            </Button>
          </div>
        </div>
      )}

      {editing && (
        <RowDialog
          table={table}
          tables={tables}
          row={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            refresh();
          }}
          onFilter={(target, next) => {
            setEditing(null);
            if (target === table.name) {
              setFilter(next);
              setOffset(0);
            } else {
              pendingFilter = { table: target, filter: next };
              navigate(`/admin/${target}`);
            }
          }}
        />
      )}
    </section>
  );
}

// Фильтр, который нужно применить после перехода в другую таблицу
let pendingFilter: { table: string; filter: Filter } | null = null;

function readPendingFilter(table: string): Filter | null {
  if (pendingFilter?.table !== table) return null;
  const { filter } = pendingFilter;
  pendingFilter = null;
  return filter;
}

function RowDialog({
  table,
  tables,
  row,
  onClose,
  onSaved,
  onFilter,
}: {
  table: AdminTable;
  tables: AdminTable[];
  row: AdminRow | null;
  onClose: () => void;
  onSaved: () => void;
  onFilter: (table: string, filter: Filter) => void;
}) {
  const toast = useToast();
  const [confirmDialog, confirm] = useConfirm();
  const [values, setValues] = useState<AdminRow>(() => initialValues(table, row));
  const [busy, setBusy] = useState(false);
  const creating = row === null;
  const id = row ? Number(row.id) : null;

  // Записи других таблиц, которые ссылаются на эту
  const related = tables.flatMap((other) =>
    other.columns
      .filter((column) => column.references === table.name)
      .map((column) => ({ table: other, column })),
  );

  const set = (name: string, value: AdminRow[string]) =>
    setValues((current) => ({ ...current, [name]: value }));

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);

    // Отправляем только изменённые поля
    const changed: AdminRow = {};

    for (const column of table.columns) {
      if (column.readonly) continue;
      const value = values[column.name];
      const before = initialValues(table, row)[column.name];

      if (creating ? value !== "" && value !== null : value !== before) {
        changed[column.name] = value;
      }
    }

    try {
      if (creating) {
        await admin.create(table.name, changed);
        toast.success("Запись создана");
      } else if (Object.keys(changed).length > 0) {
        await admin.update(table.name, id as number, changed);
        toast.success("Сохранено");
      }
      onSaved();
    } catch (error) {
      toast.error(error);
      setBusy(false);
    }
  };

  const remove = async () => {
    const agreed = await confirm(
      table.name === "users"
        ? "Пользователь будет удалён вместе со всеми его программами, тренировками и подходами. Отменить нельзя."
        : "Запись будет удалена. Связанные записи удалятся или отвяжутся по правилам базы. Отменить нельзя.",
      "Удалить",
    );

    if (!agreed) return;

    try {
      await admin.remove(table.name, id as number);
      toast.success("Удалено");
      onSaved();
    } catch (error) {
      toast.error(error);
    }
  };

  return (
    <Modal
      title={creating ? `Новая запись · ${table.label}` : `${table.label} · #${id}`}
      onClose={onClose}
      wide
    >
      <form className="form admin-form" onSubmit={submit}>
        {table.columns
          .filter((column) => !(creating && column.readonly))
          .map((column) => (
            <AdminField
              key={column.name}
              column={column}
              value={values[column.name]}
              creating={creating}
              onChange={(value) => set(column.name, value)}
              onOpen={
                column.references && values[column.name] !== null && values[column.name] !== ""
                  ? () =>
                      onFilter(column.references as string, {
                        field: "id",
                        value: Number(values[column.name]),
                        label: `ID = ${values[column.name]}`,
                      })
                  : undefined
              }
            />
          ))}

        {!creating && related.length > 0 && (
          <div className="admin-related">
            <span className="field-label">Связанные записи</span>
            <div className="admin-related-links">
              {related.map(({ table: other, column }) => (
                <button
                  key={`${other.name}.${column.name}`}
                  type="button"
                  className="chip"
                  onClick={() =>
                    onFilter(other.name, {
                      field: column.name,
                      value: id as number,
                      label: `${label(column.name)} = ${id}`,
                    })
                  }
                >
                  {other.label}
                  {other.columns.filter((c) => c.references === table.name).length > 1 &&
                    ` (${label(column.name).toLowerCase()})`}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="modal-actions admin-actions">
          {!creating && (
            <Button variant="danger" onClick={() => void remove()}>Удалить</Button>
          )}
          <Button onClick={onClose}>Отмена</Button>
          <Button variant="primary" type="submit" busy={busy}>
            {creating ? "Создать" : "Сохранить"}
          </Button>
        </div>
      </form>
      {confirmDialog}
    </Modal>
  );
}

function initialValues(table: AdminTable, row: AdminRow | null): AdminRow {
  const values: AdminRow = {};

  for (const column of table.columns) {
    const value = row?.[column.name];

    if (column.kind === "boolean") {
      values[column.name] = typeof value === "boolean" ? value : row ? false : !column.nullable ? false : null;
    } else if (column.kind === "datetime" && typeof value === "string") {
      values[column.name] = value.slice(0, 16);
    } else {
      values[column.name] = value ?? "";
    }
  }

  return values;
}

function AdminField({
  column,
  value,
  creating,
  onChange,
  onOpen,
}: {
  column: AdminColumn;
  value: AdminRow[string];
  creating: boolean;
  onChange: (value: AdminRow[string]) => void;
  onOpen?: () => void;
}) {
  const id = `admin-${column.name}`;
  const required = creating && column.required;
  const hint = [
    column.references ? `ссылка на «${column.references}»` : null,
    column.nullable && !column.readonly && column.kind !== "password" ? "можно оставить пустым" : null,
    column.hint,
  ]
    .filter(Boolean)
    .join(" · ");

  let input;

  if (column.readonly) {
    input = (
      <p className="admin-readonly" id={id}>
        {display(column, value === "" ? null : value)}
      </p>
    );
  } else if (column.choices) {
    input = (
      <select id={id} value={String(value ?? "")} required={!column.nullable} onChange={(e) => onChange(e.target.value)}>
        {column.nullable && <option value="">—</option>}
        {!column.nullable && value === "" && <option value="">Выберите</option>}
        {column.choices.map((choice) => (
          <option key={choice} value={choice}>{choice}</option>
        ))}
      </select>
    );
  } else if (column.kind === "boolean") {
    input = (
      <label className="toggle">
        <input id={id} type="checkbox" checked={value === true} onChange={(e) => onChange(e.target.checked)} />
        {value === true ? "да" : "нет"}
      </label>
    );
  } else if (column.kind === "text") {
    input = (
      <textarea
        id={id}
        rows={3}
        maxLength={column.max_length ?? undefined}
        required={required}
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  } else {
    const type =
      column.kind === "integer" || column.kind === "number"
        ? "number"
        : column.kind === "date"
          ? "date"
          : column.kind === "datetime"
            ? "datetime-local"
            : column.kind === "password"
              ? "password"
              : column.name === "email" || column.name === "invited_email"
                ? "email"
                : "text";

    input = (
      <input
        id={id}
        type={type}
        step={column.kind === "number" ? "any" : undefined}
        autoComplete={column.kind === "password" ? "new-password" : "off"}
        maxLength={column.max_length ?? undefined}
        required={required}
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }

  return (
    <div className="field admin-field">
      <label className="field-label" htmlFor={id}>
        {label(column.name)}
        <span className="admin-column-name">{column.name}</span>
      </label>
      <div className="admin-input">
        {input}
        {onOpen && (
          <Button small variant="ghost" onClick={onOpen}>
            Открыть
          </Button>
        )}
      </div>
      {hint && <span className="field-hint">{hint}</span>}
    </div>
  );
}
