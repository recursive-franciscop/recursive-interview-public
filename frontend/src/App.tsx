import React, { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { Exercise, Workout, WorkoutCreate, WorkoutItem } from "./types";
import * as api from "./api";

type ExerciseType = "strength" | "cardio" | "mobility";

function getExerciseById(exercises: Exercise[], id: number): Exercise | undefined {
  return exercises.find((e) => e.id === id);
}

export default function App() {
  // Catalog
  const [allExercises, setAllExercises] = useState<Exercise[]>([]);
  const [exercises, setExercises] = useState<Exercise[]>([]);
  const [workouts, setWorkouts] = useState<Workout[]>([]);

  // Filters
  const [q, setQ] = useState("");
  const [muscleGroup, setMuscleGroup] = useState("");
  const [exType, setExType] = useState<ExerciseType | "">("");

  // Builder
  const [workoutName, setWorkoutName] = useState("");
  const [items, setItems] = useState<WorkoutItem[]>([]);

  // UI
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");

  // Distinct filter options from the full catalog
  const muscleGroups = useMemo(() => {
    const set = new Set(allExercises.map((e) => e.muscle_group));
    return Array.from(set).sort();
  }, [allExercises]);

  // (initial data now loaded via react-query)
  const { data: initData, isLoading: initLoading, error: initError } = useQuery<{ exercises: Exercise[]; workouts: Workout[] }, Error>({
    queryKey: ["initial"],
    queryFn: api.getInitialData,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    staleTime: Infinity,
    retry: 0, // ensure only one attempt for initial load per requirement
  });

  React.useEffect(() => {
    if (initData) {
      setAllExercises(initData.exercises);
      setExercises(initData.exercises);
      setWorkouts(initData.workouts);
    }
  }, [initData]);

  React.useEffect(() => {
    if (initError) {
      setError((initError as any)?.message ?? String(initError));
    }
  }, [initError]);

  const busy = loading || initLoading;

  async function runSearch() {
    try {
      setLoading(true);
      setError("");
      const list = await api.getExercises({
        q: q || undefined,
        muscle_group: muscleGroup || undefined,
        type: exType || undefined,
      });
      setExercises(list);
    } catch (e: any) {
      setError(e?.message ?? String(e));
    } finally {
      setLoading(false);
    }
  }

  function addExercise(ex: Exercise) {
    const defaultItem: WorkoutItem =
      ex.type === "strength"
        ? { exercise_id: ex.id, sets: 3, reps: 10 }
        : { exercise_id: ex.id, duration_seconds: 300 };
    setItems((prev) => [...prev, defaultItem]);
  }

  function removeItem(idx: number) {
    setItems((prev) => prev.filter((_, i) => i !== idx));
  }

  function updateItemNumber<K extends keyof WorkoutItem>(idx: number, key: K, value: string) {
    setItems((prev) => {
      const next = [...prev];
      const n = value.trim() === "" ? undefined : Number(value);
      // @ts-ignore - allow numeric field update by key; values are number | undefined
      next[idx][key] = Number.isFinite(n) ? (n as any) : undefined;
      return next;
    });
  }

  function updateItemText(idx: number, value: string) {
    setItems((prev) => {
      const next = [...prev];
      next[idx].notes = value;
      return next;
    });
  }

  async function saveWorkout() {
    try {
      setLoading(true);
      setError("");

      if (!workoutName.trim()) {
        throw new Error("Please provide a workout name.");
      }
      if (items.length === 0) {
        throw new Error("Add at least one exercise to the workout.");
      }

      // Validate each item to mirror server rules
      for (let i = 0; i < items.length; i++) {
        const it = items[i];
        const ex = getExerciseById(allExercises, it.exercise_id);
        if (!ex) throw new Error(`Item ${i + 1}: Exercise not found (id=${it.exercise_id})`);
        const hasSetsReps = it.sets !== undefined && it.reps !== undefined;
        const hasDuration = it.duration_seconds !== undefined;
        if (!hasSetsReps && !hasDuration) {
          throw new Error(
            `Item ${i + 1}: Provide sets & reps for strength or duration_seconds for cardio/mobility`
          );
        }
      }

      const payload: WorkoutCreate = {
        name: workoutName.trim(),
        items,
      };
      await api.createWorkout(payload);

      // Refresh workouts, reset builder
      const w = await api.getWorkouts();
      setWorkouts(w);
      setWorkoutName("");
      setItems([]);
    } catch (e: any) {
      setError(e?.message ?? String(e));
    } finally {
      setLoading(false);
    }
  }

  async function deleteWorkout(id: number) {
    try {
      setLoading(true);
      setError("");
      await api.deleteWorkout(id);
      const w = await api.getWorkouts();
      setWorkouts(w);
    } catch (e: any) {
      setError(e?.message ?? String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>FitFlow Workout Builder</h1>
        <div className="status">
          {busy && <span className="badge">Loading...</span>}
          {error && <span className="error">{error}</span>}
        </div>
      </header>

      <main className="content">
        <section className="panel left">
          <h2>Exercises</h2>

          <div className="filters">
            <input
              className="input"
              placeholder="Search by name..."
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <select
              className="input"
              value={muscleGroup}
              onChange={(e) => setMuscleGroup(e.target.value)}
            >
              <option value="">All muscle groups</option>
              {muscleGroups.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
            <select
              className="input"
              value={exType}
              onChange={(e) => setExType(e.target.value as ExerciseType | "")}
            >
              <option value="">All types</option>
              <option value="strength">Strength</option>
              <option value="cardio">Cardio</option>
              <option value="mobility">Mobility</option>
            </select>
            <button className="btn" onClick={runSearch}>
              Search
            </button>
          </div>

          <ul className="list">
            {exercises.map((ex) => (
              <li key={ex.id} className="list-item">
                <div>
                  <div className="title">{ex.name}</div>
                  <div className="sub">
                    {ex.muscle_group} • {ex.type}
                    {ex.equipment ? ` • ${ex.equipment}` : ""}
                  </div>
                </div>
                <button className="btn" onClick={() => addExercise(ex)}>
                  Add
                </button>
              </li>
            ))}
            {exercises.length === 0 && <div className="muted">No exercises found.</div>}
          </ul>
        </section>

        <section className="panel right">
          <h2>Build Workout</h2>
          <div className="builder">
            <input
              className="input"
              placeholder="Workout name (e.g., Push Day)"
              value={workoutName}
              onChange={(e) => setWorkoutName(e.target.value)}
            />

            <div className="builder-items">
              {items.map((it, idx) => {
                const ex = getExerciseById(allExercises, it.exercise_id);
                const type = (ex?.type || "strength") as ExerciseType;
                return (
                  <div key={idx} className="builder-item">
                    <div className="builder-head">
                      <div className="title">{ex?.name ?? `Exercise #${it.exercise_id}`}</div>
                      <button className="btn btn-danger" onClick={() => removeItem(idx)}>
                        Remove
                      </button>
                    </div>

                    {type === "strength" ? (
                      <div className="row">
                        <label className="label">
                          Sets
                          <input
                            className="input small"
                            type="number"
                            min={1}
                            value={it.sets ?? ""}
                            onChange={(e) => updateItemNumber(idx, "sets", e.target.value)}
                          />
                        </label>
                        <label className="label">
                          Reps
                          <input
                            className="input small"
                            type="number"
                            min={1}
                            value={it.reps ?? ""}
                            onChange={(e) => updateItemNumber(idx, "reps", e.target.value)}
                          />
                        </label>
                      </div>
                    ) : (
                      <div className="row">
                        <label className="label">
                          Duration (seconds)
                          <input
                            className="input small"
                            type="number"
                            min={1}
                            value={it.duration_seconds ?? ""}
                            onChange={(e) => updateItemNumber(idx, "duration_seconds", e.target.value)}
                          />
                        </label>
                      </div>
                    )}

                    <label className="label">
                      Notes
                      <textarea
                        className="input"
                        rows={2}
                        placeholder="Optional notes..."
                        value={it.notes ?? ""}
                        onChange={(e) => updateItemText(idx, e.target.value)}
                      />
                    </label>
                  </div>
                );
              })}
              {items.length === 0 && <div className="muted">No items yet. Add exercises from the list.</div>}
            </div>

            <button className="btn primary" onClick={saveWorkout} disabled={items.length === 0}>
              Save Workout
            </button>
          </div>

          <div className="saved">
            <h3>Saved Workouts</h3>
            <ul className="list">
              {workouts.map((w) => (
                <li key={w.id} className="list-item">
                  <div>
                    <div className="title">{w.name}</div>
                    <div className="sub">{w.items.length} items</div>
                  </div>
                  <button className="btn btn-danger" onClick={() => deleteWorkout(w.id)}>
                    Delete
                  </button>
                </li>
              ))}
              {workouts.length === 0 && <div className="muted">No saved workouts.</div>}
            </ul>
          </div>
        </section>
      </main>
      <footer className="footer">Backend API at /api • React + Vite</footer>
    </div>
  );
}
