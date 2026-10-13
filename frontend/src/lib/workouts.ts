// Названия тренировки: из программы, а если её уже удалили —
// сохранённые в самой тренировке

import type { ProgramDetail, ScheduledWorkout } from "../api/types";

export function workoutNames(
  workout: ScheduledWorkout,
  programs: Map<number, ProgramDetail>,
) {
  const program = workout.program_id !== null ? programs.get(workout.program_id) : undefined;
  const day = program?.days.find((item) => item.id === workout.program_day_id);

  return {
    program,
    day,
    dayName: day?.name ?? workout.day_name ?? "Тренировка",
    programName: program?.name ?? workout.program_name ?? "",
  };
}
