// Загрузка данных, которые нужны нескольким экранам

import { exercises, programs } from "../api";
import type { Exercise, ProgramDetail } from "../api/types";

// Все программы пользователя вместе с днями и упражнениями
export async function loadProgramDetails(): Promise<ProgramDetail[]> {
  const list = await programs.list();
  return Promise.all(list.map((program) => programs.get(program.id)));
}

export async function loadExercises(): Promise<Exercise[]> {
  const list = await exercises.list();
  return list.sort((a, b) => a.name.localeCompare(b.name, "ru"));
}
