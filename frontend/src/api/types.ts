// Типы ответов и запросов API — повторяют схемы бэкенда (app/schemas)

export type WorkoutStatus = "planned" | "completed" | "skipped";

export type UserRole = "user" | "coach";

export interface User {
  id: number;
  email: string;
  username: string;
  // coach — тренер, работает со своими клиентами
  role: UserRole;
  // администратор: видит админ-панель (ADMIN_EMAILS)
  is_admin: boolean;
  created_at: string;
  updated_at: string;
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Exercise {
  id: number;
  name: string;
  description: string | null;
  muscle_group: string | null;
  equipment: string | null;
  // null — общее упражнение из справочника
  created_by_user_id: number | null;
}

export interface ExerciseInput {
  name: string;
  description: string | null;
  muscle_group: string | null;
  equipment: string | null;
}

export interface ExerciseShort {
  id: number;
  name: string;
}

export interface ProgramExercise {
  id: number;
  program_day_id: number;
  exercise_id: number;
  exercise: ExerciseShort;
  order_index: number;
  sets: number;
  target_reps: number | null;
  // верхняя граница диапазона: 8–12
  target_reps_max: number | null;
  target_weight: number | null;
  rest_seconds: number | null;
  notes: string | null;
}

export interface ProgramExerciseInput {
  exercise_id: number;
  order_index: number;
  sets: number;
  target_reps: number | null;
  // верхняя граница диапазона: 8–12
  target_reps_max: number | null;
  target_weight: number | null;
  rest_seconds: number | null;
  notes: string | null;
}

export interface ProgramDay {
  id: number;
  program_id: number;
  name: string;
  order_index: number;
  exercises: ProgramExercise[];
}

export interface Program {
  id: number;
  // владелец; null у готовых шаблонов
  user_id: number | null;
  name: string;
  description: string | null;
  // можно ли менять: программу от тренера клиент только смотрит
  can_edit: boolean;
  // тренер, который назначил программу
  assigned_by: PersonShort | null;
  source_program_id: number | null;
}

export interface ProgramDetail extends Program {
  days: ProgramDay[];
}

// Оценка после тренировки
export interface WorkoutFeedback {
  // самочувствие 1–5
  wellbeing: number | null;
  // сложность 1–10
  difficulty: number | null;
  feedback_comment: string | null;
  feedback_at: string | null;
}

export interface ScheduledWorkout extends WorkoutFeedback {
  id: number;
  // null, если программу или день потом удалили (тренировка осталась в истории)
  program_id: number | null;
  program_day_id: number | null;
  program_name: string | null;
  day_name: string | null;
  scheduled_date: string;
  status: WorkoutStatus;
}

export interface WorkoutSet {
  id: number;
  scheduled_workout_id: number;
  // null, если упражнение потом убрали из плана
  program_exercise_id: number | null;
  exercise_id: number;
  set_number: number;
  weight: number;
  reps: number;
  completed: boolean;
}

export interface WorkoutExerciseDetail {
  // null — упражнения уже нет в плане, остались только сделанные подходы
  program_exercise_id: number | null;
  exercise: ExerciseShort;
  order_index: number;
  sets: number;
  target_reps: number | null;
  // верхняя граница диапазона: 8–12
  target_reps_max: number | null;
  target_weight: number | null;
  rest_seconds: number | null;
  notes: string | null;
  performed_sets: WorkoutSet[];
}

export type WorkoutDetail = WorkoutFeedback & {
  id: number;
  program_id: number | null;
  program_name: string;
  program_day_id: number | null;
  program_day_name: string;
  scheduled_date: string;
  status: WorkoutStatus;
  // программу ведёт тренер
  coach_name: string | null;
  exercises: WorkoutExerciseDetail[];
} & CoachComment

export interface HistoryItem {
  workout_set_id: number;
  scheduled_workout_id: number;
  date: string;
  set_number: number;
  weight: number;
  reps: number;
  completed: boolean;
}

export interface RecordSet {
  weight: number;
  reps: number;
  date: string;
}

export interface ExerciseRecords {
  exercise_id: number;
  total_sets: number;
  total_reps: number;
  total_volume: number;
  last_performed: string | null;
  max_weight: RecordSet | null;
  best_estimated_1rm_set: RecordSet | null;
  best_estimated_1rm: number | null;
}

export interface StatsSummary {
  date_from: string | null;
  date_to: string | null;
  workouts_planned: number;
  workouts_completed: number;
  workouts_skipped: number;
  total_sets: number;
  total_reps: number;
  total_volume: number;
}

export interface WeeklyVolume {
  week_start: string;
  workouts: number;
  sets: number;
  reps: number;
  volume: number;
}

// Кабинет тренера

export interface PersonShort {
  id: number;
  username: string;
  email: string;
}

// on_track — «По плану», check — «Проверить», progress — «Оценить прогресс»
export type ClientFlag = "on_track" | "check" | "progress";

// inactive — давно не тренировался, low_adherence — низкое выполнение плана,
// stagnation — давно нет новых рекордов
export type FlagReason = "inactive" | "low_adherence" | "stagnation";

export interface ClientMetrics {
  workouts_completed: number;
  workouts_skipped: number;
  // прошедшие тренировки из плана, которые клиент не отметил
  workouts_missed: number;
  workouts_upcoming: number;
  // 0..1; null — за период плана не было
  adherence: number | null;
  total_sets: number;
  total_volume: number;
  new_records: number;
  // средние оценки после тренировок за период
  avg_wellbeing: number | null;
  avg_difficulty: number | null;
  last_workout: string | null;
  days_since_last_workout: number | null;
  next_workout: { id: number; date: string; program_name: string; day_name: string } | null;
  flag: ClientFlag;
  reasons: FlagReason[];
}

export type CoachingStatus = "invited" | "active" | "declined" | "ended";

export interface CoachClientLink {
  id: number;
  status: CoachingStatus;
  invited_email: string;
  created_at: string;
  responded_at: string | null;
  ended_at: string | null;
  // пусто, пока человек с этим email не зарегистрировался
  client: PersonShort | null;
  // только у активных клиентов
  metrics: ClientMetrics | null;
}

export interface CoachClientCard {
  client: PersonShort;
  link: CoachClientLink;
  metrics: ClientMetrics;
}

export interface CoachExerciseRecords extends ExerciseRecords {
  exercise_name: string;
  muscle_group: string | null;
}

export interface CoachWorkout {
  id: number;
  scheduled_date: string;
  status: WorkoutStatus;
  program_name: string;
  day_name: string;
  sets_completed: number;
  volume: number;
  wellbeing: number | null;
  difficulty: number | null;
  feedback_comment: string | null;
  coach_comment: string | null;
}

export interface KeyExercise {
  exercise_id: number;
  name: string;
  muscle_group: string | null;
  // лучший расчётный максимум на 1 повтор за период и за период до него
  best_now: number | null;
  best_before: number | null;
  // 0.06 = +6%
  change: number | null;
  sets: number;
}

// Показатели за период и за такой же период перед ним
export interface PeriodOverview {
  date_from: string;
  date_to: string;
  previous_from: string;
  previous_to: string;
  current: ClientMetrics;
  previous: ClientMetrics;
  // среднее изменение расчётной силы: 0.06 = +6%
  strength_change: number | null;
  key_exercises: KeyExercise[];
}

export interface ScheduleInput {
  start_date: string;
  weeks: number;
  // 0 = понедельник ... 6 = воскресенье
  weekdays: number[];
}

export interface CoachNote {
  id: number;
  text: string;
  // заметка видна клиенту
  shared: boolean;
  created_at: string;
  updated_at: string;
}

// Заметка тренера, которую видит клиент
export interface SharedNote {
  id: number;
  text: string;
  created_at: string;
  updated_at: string;
}

// Комментарий тренера к тренировке
export interface CoachComment {
  coach_comment: string | null;
  coach_comment_at: string | null;
  coach_comment_author: string | null;
}

// Тренер глазами клиента
export interface CoachingState {
  coach: { id: number; coach: PersonShort; since: string | null } | null;
}

// Админ-панель

export type AdminFieldKind =
  | "integer"
  | "number"
  | "boolean"
  | "date"
  | "datetime"
  | "string"
  | "text"
  | "password";

export interface AdminColumn {
  name: string;
  kind: AdminFieldKind;
  nullable: boolean;
  readonly: boolean;
  // обязательно при создании
  required: boolean;
  max_length: number | null;
  // на какую таблицу ссылается
  references: string | null;
  choices: string[] | null;
  hint: string | null;
}

export interface AdminTable {
  name: string;
  label: string;
  count: number;
  list_columns: string[];
  searchable: boolean;
  columns: AdminColumn[];
}

export type AdminRow = Record<string, string | number | boolean | null>;

export interface AdminStats {
  counts: Record<string, number>;
  new_users_week: number;
  workouts_week: number;
  active_users_week: number;
}
