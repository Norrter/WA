// Все запросы к бэкенду в одном месте

import { query, request } from "./client";
import type {
  CoachExerciseRecords,
  CoachUser,
  CoachWorkout,
  Exercise,
  ExerciseInput,
  ExerciseRecords,
  HistoryItem,
  Program,
  ProgramDay,
  ProgramDetail,
  ProgramExercise,
  ProgramExerciseInput,
  ScheduledWorkout,
  StatsSummary,
  Tokens,
  User,
  WeeklyVolume,
  WorkoutDetail,
  WorkoutSet,
  WorkoutStatus,
} from "./types";

export const auth = {
  login: (email: string, password: string) =>
    request<Tokens>("POST", "/auth/login", { email, password }),
  me: () => request<User>("GET", "/auth/me"),
};

export const users = {
  register: (data: { email: string; username: string; password: string }) =>
    request<User>("POST", "/users", data),
  update: (data: Partial<Pick<User, "email" | "username">>) =>
    request<User>("PATCH", "/users/me", data),
  changePassword: (current_password: string, new_password: string) =>
    request<void>("POST", "/users/me/password", { current_password, new_password }),
  deleteMe: () => request<void>("DELETE", "/users/me"),
};

export const exercises = {
  list: (params: { search?: string; muscle_group?: string } = {}) =>
    request<Exercise[]>("GET", `/exercises${query({ ...params, limit: 500 })}`),
  get: (id: number) => request<Exercise>("GET", `/exercises/${id}`),
  create: (data: ExerciseInput) => request<Exercise>("POST", "/exercises", data),
  update: (id: number, data: ExerciseInput) =>
    request<Exercise>("PUT", `/exercises/${id}`, data),
  remove: (id: number) => request<void>("DELETE", `/exercises/${id}`),
  history: (id: number, limit = 200) =>
    request<HistoryItem[]>("GET", `/exercises/${id}/history${query({ limit })}`),
  records: (id: number) => request<ExerciseRecords>("GET", `/exercises/${id}/records`),
};

export const programs = {
  list: () => request<Program[]>("GET", "/programs"),
  // Готовые программы, общие для всех
  templates: () => request<ProgramDetail[]>("GET", "/programs/templates"),
  copy: (id: number) => request<Program>("POST", `/programs/${id}/copy`),
  get: (id: number) => request<ProgramDetail>("GET", `/programs/${id}`),
  create: (data: { name: string; description: string | null }) =>
    request<Program>("POST", "/programs", data),
  patch: (id: number, data: { name?: string; description?: string | null }) =>
    request<Program>("PATCH", `/programs/${id}`, data),
  remove: (id: number) => request<void>("DELETE", `/programs/${id}`),

  addDay: (programId: number, name: string, order_index: number) =>
    request<ProgramDay>("POST", `/programs/${programId}/days`, { name, order_index }),
  renameDay: (programId: number, dayId: number, name: string) =>
    request<ProgramDay>("PATCH", `/programs/${programId}/days/${dayId}`, { name }),
  removeDay: (programId: number, dayId: number) =>
    request<void>("DELETE", `/programs/${programId}/days/${dayId}`),
  reorderDays: (programId: number, ids: number[]) =>
    request<ProgramDay[]>("POST", `/programs/${programId}/days/reorder`, { ids }),

  addExercise: (programId: number, dayId: number, data: ProgramExerciseInput) =>
    request<ProgramExercise>(
      "POST",
      `/programs/${programId}/days/${dayId}/exercises`,
      data,
    ),
  patchExercise: (
    programId: number,
    dayId: number,
    id: number,
    data: Partial<ProgramExerciseInput>,
  ) =>
    request<ProgramExercise>(
      "PATCH",
      `/programs/${programId}/days/${dayId}/exercises/${id}`,
      data,
    ),
  removeExercise: (programId: number, dayId: number, id: number) =>
    request<void>("DELETE", `/programs/${programId}/days/${dayId}/exercises/${id}`),
  reorderExercises: (programId: number, dayId: number, ids: number[]) =>
    request<ProgramExercise[]>(
      "POST",
      `/programs/${programId}/days/${dayId}/exercises/reorder`,
      { ids },
    ),
};

export const workouts = {
  list: (params: { date_from?: string; date_to?: string; status?: WorkoutStatus }) =>
    request<ScheduledWorkout[]>(
      "GET",
      `/scheduled-workouts${query({ ...params, limit: 500 })}`,
    ),
  full: (id: number) => request<WorkoutDetail>("GET", `/scheduled-workouts/${id}/full`),
  create: (data: { program_id: number; program_day_id: number; scheduled_date: string }) =>
    request<ScheduledWorkout>("POST", "/scheduled-workouts", data),
  generate: (data: {
    program_id: number;
    start_date: string;
    weeks: number;
    weekdays: number[];
  }) => request<ScheduledWorkout[]>("POST", "/scheduled-workouts/generate", data),
  patch: (id: number, data: { status?: WorkoutStatus; scheduled_date?: string }) =>
    request<ScheduledWorkout>("PATCH", `/scheduled-workouts/${id}`, data),
  remove: (id: number) => request<void>("DELETE", `/scheduled-workouts/${id}`),

  addSet: (
    workoutId: number,
    data: { program_exercise_id: number; set_number: number; weight: number; reps: number },
  ) => request<WorkoutSet>("POST", `/scheduled-workouts/${workoutId}/sets`, data),
  patchSet: (workoutId: number, setId: number, data: Partial<WorkoutSet>) =>
    request<WorkoutSet>("PATCH", `/scheduled-workouts/${workoutId}/sets/${setId}`, data),
  removeSet: (workoutId: number, setId: number) =>
    request<void>("DELETE", `/scheduled-workouts/${workoutId}/sets/${setId}`),
};

export const stats = {
  summary: (date_from: string, date_to: string) =>
    request<StatsSummary>("GET", `/stats/summary${query({ date_from, date_to })}`),
  weekly: (weeks: number) =>
    request<WeeklyVolume[]>("GET", `/stats/weekly-volume${query({ weeks })}`),
};

// Кабинет тренера: только чтение, доступно пользователям с ролью coach
export const coach = {
  users: (date_from: string, date_to: string) =>
    request<CoachUser[]>("GET", `/coach/users${query({ date_from, date_to })}`),
  user: (id: number) => request<User>("GET", `/coach/users/${id}`),
  summary: (id: number, date_from: string, date_to: string) =>
    request<StatsSummary>(
      "GET",
      `/coach/users/${id}/summary${query({ date_from, date_to })}`,
    ),
  weekly: (id: number, weeks: number) =>
    request<WeeklyVolume[]>("GET", `/coach/users/${id}/weekly-volume${query({ weeks })}`),
  records: (id: number) =>
    request<CoachExerciseRecords[]>("GET", `/coach/users/${id}/records`),
  workouts: (id: number, date_from: string, date_to: string, limit = 15) =>
    request<CoachWorkout[]>(
      "GET",
      `/coach/users/${id}/workouts${query({ date_from, date_to, limit })}`,
    ),
};
