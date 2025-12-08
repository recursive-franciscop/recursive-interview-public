import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import type { Exercise, Workout } from "./types";
import * as api from "./api";

vi.mock("./api", () => ({
  getExercises: vi.fn(),
  getWorkouts: vi.fn(),
  createWorkout: vi.fn(),
  deleteWorkout: vi.fn(),
}));

const sampleExercises: Exercise[] = [
  { id: 1, name: "Barbell Back Squat", muscle_group: "Legs", equipment: "Barbell", type: "strength" },
  { id: 2, name: "Running", muscle_group: "Full Body", equipment: null as any, type: "cardio" },
];

describe("App", () => {
  beforeEach(() => {
    (api.getExercises as any).mockResolvedValue(sampleExercises);
    (api.getWorkouts as any).mockResolvedValue([] as Workout[]);
    (api.createWorkout as any).mockResolvedValue({ id: 1, name: "", items: [] });
    (api.deleteWorkout as any).mockResolvedValue(undefined);
  });

  it("renders and shows initial exercises", async () => {
    render(<App />);

    // Title
    expect(await screen.findByText(/Workout Builder/i)).toBeInTheDocument();

    // Exercises from mocked API
    expect(await screen.findByText("Barbell Back Squat")).toBeInTheDocument();
    expect(await screen.findByText("Running")).toBeInTheDocument();
  });

  it("adds an exercise, validates missing name, then saves and shows in list", async () => {
    // First getWorkouts (on mount) returns [] then after save returns one workout
    (api.getWorkouts as any)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([{ id: 1, name: "Leg Day", items: [{ exercise_id: 1, sets: 3, reps: 10 }] }] as Workout[]);

    render(<App />);

    // Add an exercise
    const addButtons = await screen.findAllByRole("button", { name: /Add/i });
    await userEvent.click(addButtons[0]);

    // Save should now be enabled (one item exists)
    const saveBtn = await screen.findByRole("button", { name: /Save Workout/i });
    expect(saveBtn).toBeEnabled();

    // Click save to trigger validation (no name yet)
    await userEvent.click(saveBtn);
    expect(await screen.findByText(/Please provide a workout name\./i)).toBeInTheDocument();

    // Fill workout name
    const nameInput = screen.getByPlaceholderText(/Workout name/i);
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, "Leg Day");

    // Mock successful create
    (api.createWorkout as any).mockResolvedValue({
      id: 1,
      name: "Leg Day",
      items: [{ exercise_id: 1, sets: 3, reps: 10 }],
    });

    // Save again
    await userEvent.click(saveBtn);

    // Saved workouts list should show the new workout name
    await waitFor(async () => {
      expect(await screen.findByText("Leg Day")).toBeInTheDocument();
    });
  });
});
