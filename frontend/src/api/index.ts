// Все запросы к бэкенду в одном месте

import { query, request } from "./client";
import type {
  CoachComment,
  SharedNote,
  AdminRow,
  AdminStats,
  AdminTable,
  CoachClientCard,
  CoachClientLink,
  CoachExerciseRecords,
  CoachingState,
  CoachNote,
  CoachWorkout,
  Exercise,
  ExerciseInput,
  ExerciseRecords,
  HistoryItem,
  PeriodOverview,
  Program,
  ProgramDay,
  ProgramDetail,
  ProgramExercise,
  ProgramExerciseInput,
  ScheduledWorkout,
  ScheduleInput,
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
  patch: (
    id: number,
    data: {
      status?: WorkoutStatus;
      scheduled_date?: string;
      wellbeing?: number | null;
      difficulty?: number | null;
      feedback_comment?: string | null;
    },
  ) => request<ScheduledWorkout>("PATCH", `/scheduled-workouts/${id}`, data),
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
  // рекорды по всем упражнениям, которые делал пользователь
  records: () => request<CoachExerciseRecords[]>("GET", "/stats/records"),
  // обзор за период и за такой же период перед ним
  overview: (date_from: string, date_to: string) =>
    request<PeriodOverview>("GET", `/stats/overview${query({ date_from, date_to })}`),
  summary: (date_from: string, date_to: string) =>
    request<StatsSummary>("GET", `/stats/summary${query({ date_from, date_to })}`),
  weekly: (weeks: number) =>
    request<WeeklyVolume[]>("GET", `/stats/weekly-volume${query({ weeks })}`),
};

// Кабинет тренера: видит только своих активных клиентов, данные не меняет
export const coach = {
  clients: (date_from: string, date_to: string) =>
    request<CoachClientLink[]>("GET", `/coach/clients${query({ date_from, date_to })}`),
  invite: (email: string) => request<CoachClientLink>("POST", "/coach/clients", { email }),
  cancelInvitation: (linkId: number) =>
    request<void>("DELETE", `/coach/invitations/${linkId}`),
  end: (clientId: number) =>
    request<CoachClientLink>("POST", `/coach/clients/${clientId}/end`),

  card: (id: number, date_from: string, date_to: string) =>
    request<CoachClientCard>("GET", `/coach/clients/${id}${query({ date_from, date_to })}`),
  weekly: (id: number, weeks: number) =>
    request<WeeklyVolume[]>("GET", `/coach/clients/${id}/weekly-volume${query({ weeks })}`),
  records: (id: number) =>
    request<CoachExerciseRecords[]>("GET", `/coach/clients/${id}/records`),
  workouts: (
    id: number,
    params: { date_from?: string; date_to?: string; limit?: number; order?: "asc" | "desc" },
  ) =>
    request<CoachWorkout[]>("GET", `/coach/clients/${id}/workouts${query({ limit: 15, ...params })}`),
  overview: (id: number, date_from: string, date_to: string) =>
    request<PeriodOverview>(
      "GET",
      `/coach/clients/${id}/overview${query({ date_from, date_to })}`,
    ),
  exerciseHistory: (id: number, exerciseId: number, limit = 200) =>
    request<HistoryItem[]>(
      "GET",
      `/coach/clients/${id}/exercises/${exerciseId}/history${query({ limit })}`,
    ),

  programs: (id: number) => request<Program[]>("GET", `/coach/clients/${id}/programs`),
  assign: (id: number, program_id: number, schedule: ScheduleInput | null) =>
    request<{ program_id: number; workouts_created: number }>(
      "POST",
      `/coach/clients/${id}/programs`,
      { program_id, schedule },
    ),
  schedule: (id: number, programId: number, schedule: ScheduleInput) =>
    request<{ program_id: number; workouts_created: number }>(
      "POST",
      `/coach/clients/${id}/programs/${programId}/schedule`,
      schedule,
    ),

  notes: (id: number) => request<CoachNote[]>("GET", `/coach/clients/${id}/notes`),
  addNote: (id: number, text: string, shared: boolean) =>
    request<CoachNote>("POST", `/coach/clients/${id}/notes`, { text, shared }),
  updateNote: (noteId: number, changes: { text?: string; shared?: boolean }) =>
    request<CoachNote>("PATCH", `/coach/notes/${noteId}`, changes),
  workout: (id: number, workoutId: number) =>
    request<WorkoutDetail>("GET", `/coach/clients/${id}/workouts/${workoutId}`),
  comment: (id: number, workoutId: number, text: string) =>
    request<CoachComment>("PUT", `/coach/clients/${id}/workouts/${workoutId}/comment`, { text }),
  removeNote: (noteId: number) => request<void>("DELETE", `/coach/notes/${noteId}`),
};

// Тренер глазами клиента: текущий тренер и его заметки для клиента
export const coaching = {
  state: () => request<CoachingState>("GET", "/coaching"),
  notes: () => request<SharedNote[]>("GET", "/coaching/notes"),
  end: () => request<CoachingState>("POST", "/coaching/end"),
};

// Админ-панель: любые данные любой таблицы (ADMIN_EMAILS)
export const admin = {
  stats: () => request<AdminStats>("GET", "/admin/stats"),
  tables: () => request<AdminTable[]>("GET", "/admin/tables"),
  rows: (
    table: string,
    params: {
      q?: string;
      field?: string;
      value?: string | number;
      limit?: number;
      offset?: number;
      sort?: string;
      order?: "asc" | "desc";
    },
  ) =>
    request<{ total: number; rows: AdminRow[] }>(
      "GET",
      `/admin/tables/${table}/rows${query(params)}`,
    ),
  row: (table: string, id: number) =>
    request<AdminRow>("GET", `/admin/tables/${table}/rows/${id}`),
  create: (table: string, values: AdminRow) =>
    request<AdminRow>("POST", `/admin/tables/${table}/rows`, values),
  update: (table: string, id: number, values: AdminRow) =>
    request<AdminRow>("PATCH", `/admin/tables/${table}/rows/${id}`, values),
  remove: (table: string, id: number) =>
    request<void>("DELETE", `/admin/tables/${table}/rows/${id}`),
};
