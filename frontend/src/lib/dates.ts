// Даты в формате API (YYYY-MM-DD) всегда считаются по местному времени

export const WEEKDAYS_SHORT = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"];

const MONTHS_GENITIVE = [
  "января", "февраля", "марта", "апреля", "мая", "июня",
  "июля", "августа", "сентября", "октября", "ноября", "декабря",
];

const MONTHS = [
  "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
  "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
];

export function toISO(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function fromISO(value: string): Date {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function today(): string {
  return toISO(new Date());
}

export function addDays(value: string, days: number): string {
  const date = fromISO(value);
  date.setDate(date.getDate() + days);
  return toISO(date);
}

// 0 = понедельник ... 6 = воскресенье
export function weekdayIndex(value: string): number {
  return (fromISO(value).getDay() + 6) % 7;
}

export function startOfWeek(value: string): string {
  return addDays(value, -weekdayIndex(value));
}

export function monthTitle(year: number, month: number): string {
  return `${MONTHS[month]} ${year}`;
}

// «12 октября», а для другого года — «12 октября 2025»
export function formatDay(value: string): string {
  const date = fromISO(value);
  const base = `${date.getDate()} ${MONTHS_GENITIVE[date.getMonth()]}`;
  return date.getFullYear() === new Date().getFullYear()
    ? base
    : `${base} ${date.getFullYear()}`;
}

// «пн, 12 октября»
export function formatDayWithWeekday(value: string): string {
  return `${WEEKDAYS_SHORT[weekdayIndex(value)]}, ${formatDay(value)}`;
}

// «сегодня», «завтра», «вчера» или дата
export function relativeDay(value: string): string {
  const now = today();

  if (value === now) return "Сегодня";
  if (value === addDays(now, 1)) return "Завтра";
  if (value === addDays(now, -1)) return "Вчера";

  return formatDayWithWeekday(value);
}
