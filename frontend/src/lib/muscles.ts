// Порядок групп мышц в фильтрах и цвет метки у каждой

export const MUSCLE_ORDER = [
  "Грудь",
  "Спина",
  "Ноги",
  "Ягодицы",
  "Плечи",
  "Бицепс",
  "Трицепс",
  "Пресс",
];

export function sortMuscleGroups(groups: Iterable<string>): string[] {
  return [...new Set(groups)].sort((a, b) => {
    const indexA = MUSCLE_ORDER.indexOf(a);
    const indexB = MUSCLE_ORDER.indexOf(b);
    return (indexA === -1 ? 99 : indexA) - (indexB === -1 ? 99 : indexB) || a.localeCompare(b);
  });
}
