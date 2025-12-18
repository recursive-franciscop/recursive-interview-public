# Workout Builder (FastAPI + React)

A simple full-stack app to build custom workouts from a list of exercises.

- Backend: FastAPI (Python) with in-memory storage
- Frontend: React (Vite + TypeScript)
- Create workouts by selecting exercises and specifying sets/reps or duration
- View and delete saved workouts

## Project Structure

- backend/
  - main.py — FastAPI app (endpoints, models, in-memory data)
  - requirements.txt — Python dependencies
- frontend/ (to be added)
  - Vite + React + TypeScript app
- README.md — Setup and usage instructions

## Prerequisites

- Python 3.9+ (3.11+ recommended)
- Node.js 18+ and npm

---

## Quick Start

Makefile shortcuts:
- First-time setup: make init
- Install dependencies: make install
- Start backend (from venv): source .venv/bin/activate && make backend
  - Or without activating venv: make backend UVICORN=.venv/bin/uvicorn
- Start frontend: make frontend
- Start both and watch: make dev (Ctrl+C to stop)
- Stop any backgrounded dev procs: make stop

--

## Backend Setup (FastAPI)

1) Create and activate a virtual environment
- macOS/Linux:
  - python3 -m venv .venv
  - source .venv/bin/activate
- Windows (PowerShell):
  - py -m venv .venv
  - .venv\Scripts\Activate.ps1

2) Install dependencies
- pip install -r backend/requirements.txt

3) Run the API locally
- uvicorn backend.main:app --reload --port 8000

4) Verify it’s running
- Health check: http://localhost:8000/api/health
- API docs (Swagger UI): http://localhost:8000/docs

### Configuration (.env)

- Copy the example file and set your variables:
  - cp backend/.env.example backend/.env
  - Edit backend/.env and set at minimum:
    - OPENAI_API_KEY=your_openai_api_key
    - Optional: OPENAI_BASE_URL=... (for OpenAI-compatible providers or gateways)
    - Optional: OPENAI_MODEL=gpt-4o-mini

- Exercises source (network JSON):
The backend loads exercises at startup; workouts remain in-memory and reset on server restart.

- Remote exercises fetch SSL options (for environments with custom roots/corporate proxies):
  - EXERCISES_CA_BUNDLE=/path/to/custom/ca.pem (overrides default certifi bundle if set)
  - EXERCISES_SSL_VERIFY=true|false (set to false only for local debugging; not recommended for production)
  - EXERCISES_BEARER_TOKEN=... (optional Authorization: Bearer token if your JSON requires auth)

---

## Frontend Setup (React + Vite)

The React app will be scaffolded in the `frontend/` directory. Once created, follow these steps:

1) Install dependencies
- cd frontend
- npm install

2) Run the dev server
- npm run dev

3) Open the app
- http://localhost:5173

The frontend will connect to the API at `http://localhost:8000` by default.

Environment variable support (to be wired in during frontend scaffolding):
- VITE_API_BASE_URL=http://localhost:8000

---

## API Summary

- GET /api/health — Simple health check
- GET /api/exercises — List exercises
  - Query params: q (search by name), muscle_group, type
- GET /api/workouts — List all saved workouts
- GET /api/workouts/{workout_id} — Get a single workout
- POST /api/workouts — Create a workout
  - Body:
    {
      "name": "Push Day",
      "items": [
        { "exercise_id": 2, "sets": 5, "reps": 5, "notes": "Heavy" },
        { "exercise_id": 10, "duration_seconds": 300 }
      ]
    }
  - Validation: each item must reference a valid exercise and include either (sets AND reps) or duration_seconds
- DELETE /api/workouts/{workout_id} — Delete a workout

### AI Chat Endpoint

- POST /api/ai/chat — Basic chat completion using an OpenAI-compatible model
  - Request Body (choose either prompt or messages):
    {
      "prompt": "Suggest a 3-exercise push day workout focused on strength.",
      "model": "gpt-4o-mini",
      "temperature": 0.7
    }

    or

    {
      "messages": [
        { "role": "system", "content": "You are a helpful fitness coach." },
        { "role": "user", "content": "Suggest a 3-exercise push day workout focused on strength." }
      ],
      "model": "gpt-4o-mini",
      "temperature": 0.7
    }
  - Response:
    {
      "reply": "...model output text...",
      "model": "gpt-4o-mini"
    }

- cURL quick test (after starting the backend and setting backend/.env):
  curl -s http://localhost:8000/api/ai/chat \
    -H "Content-Type: application/json" \
    -d '{"prompt":"Say hello from the Workout Builder API","model":"gpt-4o-mini"}' | jq .

---

## Notes

- CORS is enabled in the backend to allow the Vite dev server.
- This project currently uses in-memory persistence for workouts. Optional enhancements include:
  - Persisting workouts to localStorage on the client
  - Adding SQLite or Postgres persistence on the server
