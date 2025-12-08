from fastapi.testclient import TestClient
import importlib
import types

# Import the app
import backend.main as main

client = TestClient(main.app)


def reset_state():
    # Reset in-memory datastore for isolated tests
    main.WORKOUTS = []
    main.WORKOUT_ID_COUNTER = 1
    # Provide a small deterministic exercise catalog
    main.EXERCISES = [
        main.Exercise(id=1, name="Squat", muscle_group="Legs", equipment="Barbell", type="strength"),
        main.Exercise(id=2, name="Run", muscle_group="Full Body", equipment=None, type="cardio"),
        main.Exercise(id=3, name="Plank", muscle_group="Core", equipment=None, type="mobility"),
    ]


def test_health():
    reset_state()
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_list_exercises_filters():
    reset_state()
    # No filter
    r = client.get("/api/exercises")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 3

    # Query by name
    r = client.get("/api/exercises", params={"q": "squ"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1 and data[0]["name"] == "Squat"

    # Filter by type
    r = client.get("/api/exercises", params={"type": "cardio"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1 and data[0]["type"] == "cardio"

    # Filter by muscle_group (case-insensitive)
    r = client.get("/api/exercises", params={"muscle_group": "legs"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1 and data[0]["muscle_group"].lower() == "legs"


def test_create_workout_validation_errors():
    reset_state()
    # Missing items
    r = client.post("/api/workouts", json={"name": "Test", "items": []})
    assert r.status_code == 400

    # Exercise not found
    r = client.post(
        "/api/workouts",
        json={
            "name": "Test",
            "items": [{"exercise_id": 999, "sets": 3, "reps": 10}],
        },
    )
    assert r.status_code == 400

    # Missing prescription
    r = client.post(
        "/api/workouts",
        json={
            "name": "Test",
            "items": [{"exercise_id": 1}],
        },
    )
    assert r.status_code == 400


def test_create_list_delete_workout():
    reset_state()

    # Create a valid workout (strength)
    r = client.post(
        "/api/workouts",
        json={
            "name": "Leg Day",
            "items": [{"exercise_id": 1, "sets": 3, "reps": 10}],
        },
    )
    assert r.status_code == 201
    created = r.json()
    assert created["id"] == 1

    # List workouts shows the new workout
    r = client.get("/api/workouts")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1 and data[0]["name"] == "Leg Day"

    # Delete it
    r = client.delete("/api/workouts/1")
    assert r.status_code == 204

    # Ensure list is empty
    r = client.get("/api/workouts")
    assert r.status_code == 200
    assert r.json() == []
