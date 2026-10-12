// Типы ответов и запросов API — повторяют схемы бэкенда (app/schemas)

export type WorkoutStatus = "planned" | "completed" | "skipped";

export type UserRole = "user" | "coach";

export interface User {
  id: number;
  email: string;
  username: string;
  // coach — тренер, видит статистику всех пользователей
  role: UserRole;
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
  name: string;
  description: string | null;
}

export interface ProgramDetail extends Program {
  days: ProgramDay[];
}

export interface ScheduledWorkout {
  id: number;
  program_id: number;
  program_day_id: number;
  scheduled_date: string;
  status: WorkoutStatus;
}

export interface WorkoutSet {
  id: number;
  scheduled_workout_id: number;
  program_exercise_id: number;
  set_number: number;
  weight: number;
  reps: number;
  completed: boolean;
}

export interface WorkoutExerciseDetail {
  program_exercise_id: number;
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

export interface WorkoutDetail {
  id: number;
  program_id: number;
  program_name: string;
  program_day_id: number;
  program_day_name: string;
  scheduled_date: string;
  status: WorkoutStatus;
  exercises: WorkoutExerciseDetail[];
}

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

export interface CoachUser {
  id: number;
  email: string;
  username: string;
  role: UserRole;
  created_at: string;
  programs: number;
  workouts_planned: number;
  workouts_completed: number;
  workouts_skipped: number;
  total_sets: number;
  total_volume: number;
  // последняя выполненная тренировка за всё время
  last_workout: string | null;
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
}
