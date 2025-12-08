export type Exercise = {
  id: number;
  name: string;
  muscle_group: string;
  equipment?: string | null;
  // backend uses: "strength" | "cardio" | "mobility"
  type: string;
};

export type WorkoutItem = {
  exercise_id: number;
  sets?: number;
  reps?: number;
  duration_seconds?: number;
  notes?: string;
};

export type Workout = {
  id: number;
  name: string;
  items: WorkoutItem[];
};

export type WorkoutCreate = {
  name: string;
  items: WorkoutItem[];
};
