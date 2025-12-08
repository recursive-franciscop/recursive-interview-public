import type { Exercise, Workout, WorkoutCreate } from "./types";

function buildQuery(params: Record<string, string | undefined>) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v && v.trim().length > 0) qs.set(k, v);
  });
  const s = qs.toString();
  return s ? `?${s}` : "";
}

// Use relative /api path so Vite dev server proxy forwards to FastAPI
const API_BASE = "/api";

// Dedupe in-flight requests by method+URL to avoid duplicate network calls
const inflight = new Map<string, Promise<any>>();

async function handleJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    let detail = text;
    try {
      const data = JSON.parse(text);
      detail = (data as any)?.detail ?? text;
    } catch {
      // Not JSON, keep raw text
    }
    throw new Error(detail || `Request failed with status ${res.status}`);
  }
  // On success, parse JSON once
  return res.json() as Promise<T>;
}

function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const key = `${init?.method || "GET"} ${url}`;
  const existing = inflight.get(key) as Promise<T> | undefined;
  if (existing) return existing;
  const p = fetch(url, init)
    .then((res) => handleJson<T>(res))
    .finally(() => inflight.delete(key));
  inflight.set(key, p as Promise<any>);
  return p;
}

export async function getHealth(): Promise<{ status: string }> {
  return fetchJson(`${API_BASE}/health`);
}

export async function getExercises(params?: {
  q?: string;
  muscle_group?: string;
  type?: string;
}): Promise<Exercise[]> {
  return fetchJson(`${API_BASE}/exercises${buildQuery(params ?? {})}`);
}

export async function getWorkouts(): Promise<Workout[]> {
  return fetchJson(`${API_BASE}/workouts`);
}

export async function createWorkout(payload: WorkoutCreate): Promise<Workout> {
  return fetchJson(`${API_BASE}/workouts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function deleteWorkout(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/workouts/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const text = await res.text();
    let detail = text;
    try {
      const data = JSON.parse(text);
      detail = (data as any)?.detail ?? text;
    } catch {
      // Not JSON, keep raw text
    }
    throw new Error(detail || `Delete failed with status ${res.status}`);
  }
}

// Cached initial data loader; clears cache on failure so a subsequent call can retry once
let initialDataPromise: Promise<{ exercises: Exercise[]; workouts: Workout[] }> | null = null;
export async function getInitialData(): Promise<{ exercises: Exercise[]; workouts: Workout[] }> {
  if (initialDataPromise) return initialDataPromise;
  initialDataPromise = (async () => {
    // Gate on health to avoid multiple failing proxy attempts when backend is down
    await getHealth();
    const [exercises, workouts] = await Promise.all([getExercises(), getWorkouts()]);
    return { exercises, workouts };
  })();
  try {
    return await initialDataPromise;
  } catch (e) {
    // On failure, clear so the caller can choose to retry later
    initialDataPromise = null;
    throw e;
  }
}
