// Все запросы к бэкенду в одном месте

import { query, request } from "./client";
import type {
  Anthropometry,
  BodyWeightEntry,
  ClientNutrition,
  Lead,
  LeadInput,
  LeadStatus,
  Offer,
  Food,
  FoodEntry,
  FoodEntryInput,
  Macros,
  NutritionCalculation,
  NutritionDay,
  NutritionDaySummary,
  NutritionProfile,
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
  verifyEmail: (token: string) =>
    request<{ email: string; email_verified: boolean }>("POST", "/auth/verify-email", { token }),
  resendVerification: () => request<void>("POST", "/auth/verify-email/resend"),
};

export const users = {
  register: (data: { email: string; username: string; password: string }) =>
    request<User>("POST", "/users", data),
  update: (data: Partial<Pick<User, "email" | "username" | "body_weight">>) =>
    request<User>("PATCH", "/users/me", data),
  changePassword: (current_password: string, new_password: string) =>
    request<void>("POST", "/users/me/password", { current_password, new_password }),
  deleteMe: () => request<void>("DELETE", "/users/me"),
};

// Журнал веса тела
export const bodyWeight = {
  list: (date_from?: string, date_to?: string) =>
    request<BodyWeightEntry[]>("GET", `/body-weight${query({ date_from, date_to })}`),
  add: (weight: number, date?: string) =>
    request<BodyWeightEntry>("POST", "/body-weight", { weight, date }),
  remove: (id: number) => request<void>("DELETE", `/body-weight/${id}`),
};

export const publicApi = {
  offers: () => request<Offer[]>("GET", "/public/offers"),
  sendLead: (data: LeadInput) => request<{ id: number }>("POST", "/public/leads", data),
};

export const leads = {
  list: (status?: LeadStatus) => request<Lead[]>("GET", `/leads${query({ status })}`),
  update: (id: number, changes: { status?: LeadStatus; note?: string }) =>
    request<Lead>("PATCH", `/leads/${id}`, changes),
  remove: (id: number) => request<void>("DELETE", `/leads/${id}`),
};

export const nutrition = {
  calculate: (data: Anthropometry & { weight?: number | null }) =>
    request<NutritionCalculation>("POST", "/nutrition/calculate", data),
  profile: () => request<NutritionProfile | null>("GET", "/nutrition/profile"),
  saveProfile: (data: Anthropometry & { targets?: Macros | null }) =>
    request<NutritionProfile>("PUT", "/nutrition/profile", data),
  day: (date: string) => request<NutritionDay>("GET", `/nutrition/day${query({ date })}`),
  summary: (date_from: string, date_to: string) =>
    request<NutritionDaySummary[]>("GET", `/nutrition/summary${query({ date_from, date_to })}`),
  addEntry: (data: FoodEntryInput) => request<FoodEntry>("POST", "/nutrition/entries", data),
  updateEntry: (id: number, data: Partial<FoodEntryInput>) =>
    request<FoodEntry>("PATCH", `/nutrition/entries/${id}`, data),
  removeEntry: (id: number) => request<void>("DELETE", `/nutrition/entries/${id}`),
  foods: (q?: string) => request<Food[]>("GET", `/nutrition/foods${query({ q })}`),
  removeFood: (id: number) => request<void>("DELETE", `/nutrition/foods/${id}`),
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
  // Готовые программы — заготовки только для тренера (назначить клиенту)
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
  // «Отменить все»: убрать все запланированные тренировки (выполненные,
  // пропущенные и начатые остаются). dry_run — только посчитать
  cancelAll: (data: { dry_run?: boolean } = {}) =>
    request<{ count: number }>("POST", "/scheduled-workouts/cancel-all", data),

  addSet: (
    workoutId: number,
    data: {
      program_exercise_id?: number;
      workout_exercise_id?: number;
      set_number: number;
      weight: number;
      reps: number;
    },
  ) => request<WorkoutSet>("POST", `/scheduled-workouts/${workoutId}/sets`, data),

  // Правки плана во время тренировки: программа не меняется.
  // Каждый запрос возвращает тренировку целиком.
  customize: (id: number) =>
    request<WorkoutDetail>("POST", `/scheduled-workouts/${id}/customize`),
  addExercise: (
    id: number,
    data: { exercise_id: number; sets?: number; target_reps?: number | null; target_weight?: number | null },
  ) => request<WorkoutDetail>("POST", `/scheduled-workouts/${id}/exercises`, data),
  changeExercise: (
    id: number,
    itemId: number,
    data: { exercise_id?: number; sets?: number },
  ) => request<WorkoutDetail>("PATCH", `/scheduled-workouts/${id}/exercises/${itemId}`, data),
  moveExercise: (id: number, itemId: number, direction: "up" | "down") =>
    request<WorkoutDetail>("POST", `/scheduled-workouts/${id}/exercises/${itemId}/move`, {
      direction,
    }),
  removeExercise: (id: number, itemId: number) =>
    request<WorkoutDetail>("DELETE", `/scheduled-workouts/${id}/exercises/${itemId}`),
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
  bodyWeight: (id: number, date_from?: string) =>
    request<BodyWeightEntry[]>("GET", `/coach/clients/${id}/body-weight${query({ date_from })}`),
  nutrition: (id: number, date?: string) =>
    request<ClientNutrition>("GET", `/coach/clients/${id}/nutrition${query({ date })}`),
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
