from typing import List, Optional, Dict
import os
import logging
import json
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Schemas (re-exported for backward compatibility with tests)
from backend.schemas import (
    Exercise,
    WorkoutItem,
    Workout,
    WorkoutCreate,
    ChatMessage,
    ChatRequest,
    ChatResult,
    AIWorkoutPlan,
    AIWorkoutProgram,
)

# Services
from backend.services.exercises import load_exercises_from_uri

# Optional AI client
try:
    from openai import OpenAI as _OpenAI
except ImportError:  # pragma: no cover
    _OpenAI = None

# -------------------------
# Logging & Config
# -------------------------
# Load .env from project root and backend/.env (both supported)
load_dotenv()
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=False)

LOG_LEVEL_NAME = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_NAME, logging.INFO)

logger = logging.getLogger("workout_backend")
logger.setLevel(LOG_LEVEL)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    logger.addHandler(_handler)
logger.info("Logger configured level=%s", LOG_LEVEL_NAME)

app = FastAPI(title="FitFlow Workout Builder API", version="1.0.0")

# AI client initialization (optional)
OPENAI_MODEL_DEFAULT = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
client = None
if _OpenAI and os.getenv("OPENAI_API_KEY"):
    client = _OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL") or None,
    )
    logger.info("OpenAI client initialized with model=%s", OPENAI_MODEL_DEFAULT)
else:
    logger.info("OpenAI client not configured; AI routes will return 500 until configured")

# CORS (allow React dev server ports in dev)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,*")
allow_origins = [o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("CORS middleware configured for local dev origins")

# -------------------------
# Data store
# -------------------------
EXERCISES_JSON_URI = ""
EXERCISES_BEARER_TOKEN = os.getenv("EXERCISES_BEARER_TOKEN")

# Attempt load; fallback to seeds if empty
EXERCISES: List[Exercise] = []
_loaded: List[Exercise] = []
if EXERCISES_JSON_URI:
    _loaded = load_exercises_from_uri(EXERCISES_JSON_URI, EXERCISES_BEARER_TOKEN)
if _loaded:
    EXERCISES = _loaded
    logger.info("Loaded %d exercises from remote source", len(EXERCISES))
else:
    EXERCISES = [
        Exercise(id=1, name="Barbell Back Squat", muscle_group="Legs", equipment="Barbell", type="strength"),
        Exercise(id=2, name="Barbell Bench Press", muscle_group="Chest", equipment="Barbell", type="strength"),
        Exercise(id=3, name="Deadlift", muscle_group="Back", equipment="Barbell", type="strength"),
        Exercise(id=4, name="Overhead Press", muscle_group="Shoulders", equipment="Barbell", type="strength"),
        Exercise(id=5, name="Pull-Up", muscle_group="Back", equipment="Pull-up Bar", type="strength"),
        Exercise(id=6, name="Push-Up", muscle_group="Chest", equipment=None, type="strength"),
        Exercise(id=7, name="Dumbbell Row", muscle_group="Back", equipment="Dumbbells", type="strength"),
        Exercise(id=8, name="Plank", muscle_group="Core", equipment=None, type="mobility"),
        Exercise(id=9, name="Running", muscle_group="Full Body", equipment=None, type="cardio"),
        Exercise(id=10, name="Jump Rope", muscle_group="Full Body", equipment="Jump Rope", type="cardio"),
        Exercise(id=11, name="Lunge", muscle_group="Legs", equipment=None, type="strength"),
        Exercise(id=12, name="Bicep Curl", muscle_group="Arms", equipment="Dumbbells", type="strength"),
        Exercise(id=13, name="Tricep Dip", muscle_group="Arms", equipment="Bench", type="strength"),
    ]
    logger.info("Loaded %d seed exercises (remote source unavailable)", len(EXERCISES))

WORKOUTS: List[Workout] = []
WORKOUT_ID_COUNTER = 1


def get_exercise_or_none(ex_id: int) -> Optional[Exercise]:
    return next((e for e in EXERCISES if e.id == ex_id), None)


# -------------------------
# Routes
# -------------------------
@app.get("/api/health")
def health():
    logger.info("Health check requested")
    return {"status": "ok"}


@app.post("/api/ai/chat", response_model=ChatResult)
def ai_chat(payload: ChatRequest):
    if not (client and os.getenv("OPENAI_API_KEY")):
        logger.error("AI chat requested but AI client not configured")
        raise HTTPException(status_code=500, detail="AI not configured: install 'openai' and set OPENAI_API_KEY on the server")

    messages: List[Dict[str, str]] = []
    if payload.messages:
        messages = [{"role": m.role, "content": m.content} for m in payload.messages]
    elif payload.prompt:
        messages = [{"role": "user", "content": payload.prompt}]
    else:
        logger.warning("AI chat request missing 'messages' and 'prompt'")
        raise HTTPException(status_code=400, detail="Provide either 'messages' or 'prompt'")

    model = payload.model or OPENAI_MODEL_DEFAULT
    logger.info("AI chat request with model=%s messages=%d", model, len(messages))

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=payload.temperature,
        )
        reply = completion.choices[0].message.content or ""
        logger.info("AI chat success (model=%s, reply_len=%d)", model, len(reply))
        return ChatResult(reply=reply, model=model)
    except Exception as e:  # pragma: no cover (network)
        logger.error("AI request failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI request failed: {e}")


class AIPlanRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    name: Optional[str] = None


@app.post("/api/ai/plan", response_model=AIWorkoutPlan)
def ai_plan(payload: AIPlanRequest):
    if not (client and os.getenv("OPENAI_API_KEY")):
        logger.error("AI plan requested but AI client not configured")
        raise HTTPException(status_code=500, detail="AI not configured: install 'openai' and set OPENAI_API_KEY on the server")

    system_prompt = (
        """
You are a helpful workout planning assistant.
Return ONLY valid JSON that strictly matches this schema: {
  "name": string,
  "items": [ {
    "exercise": {
      "exercise_id": number,
      "name": string,
      "equipment_type": string|null,
      "target_muscle_groups": { "primary": string[], "secondary": string[] },
      "utility": string|null
    },
    "prescription": {
      "exercise_id": number,
      "sets": number|null,
      "reps": number|null,
      "duration_seconds": number|null,
      "notes": string|null
    }
  } ]
}.
Rules: The prescription must include either sets & reps for strength OR duration_seconds for cardio/mobility.
Use realistic values. Do not include any text outside the JSON.
"""
    ).strip()

    name_hint = payload.name or "Custom Workout"
    user_prompt = (
        f"User query: {payload.prompt}\n"
        f"Output a plan named '{name_hint}'."
    )

    model = payload.model or OPENAI_MODEL_DEFAULT
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        content = completion.choices[0].message.content or "{}"
        data = json.loads(content)
        # Validate against our schema
        plan = AIWorkoutPlan(**data)
        logger.info("AI workout plan generated name=%s items=%d", plan.name, len(plan.items))
        return plan
    except Exception as e:
        logger.error("AI plan generation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI plan generation failed: {e}")


class AIProgramRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    name: Optional[str] = None


@app.post("/api/ai/program", response_model=AIWorkoutProgram)
def ai_program(payload: AIProgramRequest):
    if not (client and os.getenv("OPENAI_API_KEY")):
        logger.error("AI program requested but AI client not configured")
        raise HTTPException(status_code=500, detail="AI not configured: install 'openai' and set OPENAI_API_KEY on the server")

    system_prompt = (
        """
You are a helpful workout planning assistant.
Return ONLY valid JSON that strictly matches this schema: {
  "name": string,
  "days": [ {
    "name": string,
    "items": [ {
      "exercise": {
        "exercise_id": number,
        "name": string,
        "equipment_type": string|null,
        "target_muscle_groups": { "primary": string[], "secondary": string[] },
        "utility": string|null
      },
      "prescription": {
        "exercise_id": number,
        "sets": number|null,
        "reps": number|null,
        "duration_seconds": number|null,
        "notes": string|null
      }
    } ]
  } ],
  "suggestions": [ { "exercise": { ... }, "prescription": { ... } } ] | null
}.
Rules: The prescription must include either sets & reps for strength OR duration_seconds for cardio/mobility.
Use realistic values. Do not include any text outside the JSON.
"""
    ).strip()

    name_hint = payload.name or "Custom Program"
    user_prompt = (
        f"User query: {payload.prompt}\n"
        f"Output a multi-day program named '{name_hint}'."
    )

    model = payload.model or OPENAI_MODEL_DEFAULT
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        content = completion.choices[0].message.content or "{}"
        data = json.loads(content)
        program = AIWorkoutProgram(**data)
        logger.info("AI workout program generated name=%s days=%d", program.name, len(program.days))
        return program
    except Exception as e:
        logger.error("AI program generation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI program generation failed: {e}")


@app.get("/api/exercises", response_model=List[Exercise])
def list_exercises(
    q: Optional[str] = None,
    muscle_group: Optional[str] = None,
    type: Optional[str] = None,
):
    logger.info("List exercises requested q=%s muscle_group=%s type=%s", q, muscle_group, type)
    results = EXERCISES
    if q:
        q_lower = q.lower()
        results = [e for e in results if q_lower in e.name.lower()]
    if muscle_group:
        results = [e for e in results if e.muscle_group.lower() == muscle_group.lower()]
    if type:
        results = [e for e in results if e.type.lower() == type.lower()]
    logger.info("List exercises returning %d results", len(results))
    return results


@app.get("/api/workouts", response_model=List[Workout])
def list_workouts():
    logger.info("List workouts requested (count=%d)", len(WORKOUTS))
    return WORKOUTS


@app.get("/api/workouts/{workout_id}", response_model=Workout)
def get_workout(workout_id: int):
    logger.info("Get workout requested id=%d", workout_id)
    workout = next((w for w in WORKOUTS if w.id == workout_id), None)
    if not workout:
        logger.warning("Workout not found id=%d", workout_id)
        raise HTTPException(status_code=404, detail="Workout not found")
    return workout


@app.post("/api/workouts", response_model=Workout, status_code=201)
def create_workout(payload: WorkoutCreate):
    global WORKOUT_ID_COUNTER

    if not payload.items:
        logger.warning("Create workout rejected: no items provided")
        raise HTTPException(status_code=400, detail="Workout must contain at least one item")

    # Validate prescription
    for i, item in enumerate(payload.items, start=1):
        ex = get_exercise_or_none(item.exercise_id)
        if not ex:
            logger.warning("Create workout rejected: exercise not found (item=%d, id=%s)", i, item.exercise_id)
            raise HTTPException(status_code=400, detail=f"Item {i}: Exercise not found (id={item.exercise_id})")

        has_sets_reps = item.sets is not None and item.reps is not None
        has_duration = item.duration_seconds is not None
        if not (has_sets_reps or has_duration):
            logger.warning("Create workout rejected: invalid prescription (item=%d, id=%s)", i, item.exercise_id)
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Item {i}: Must provide either sets & reps for strength or "
                    f"duration_seconds for cardio/mobility"
                ),
            )

    workout = Workout(id=WORKOUT_ID_COUNTER, name=payload.name, items=payload.items)
    WORKOUTS.append(workout)
    WORKOUT_ID_COUNTER += 1
    logger.info("Created workout id=%d name=%s items=%d", workout.id, workout.name, len(workout.items))
    return workout


@app.delete("/api/workouts/{workout_id}", status_code=204)
def delete_workout(workout_id: int):
    global WORKOUTS
    logger.info("Delete workout requested id=%d", workout_id)
    before = len(WORKOUTS)
    WORKOUTS = [w for w in WORKOUTS if w.id != workout_id]
    after = len(WORKOUTS)
    if before == after:
        logger.warning("Delete workout failed: not found id=%d", workout_id)
        raise HTTPException(status_code=404, detail="Workout not found")
    logger.info("Deleted workout id=%d", workout_id)
    return


# Root endpoint
@app.get("/")
def root():
    logger.info("Root endpoint requested")
    return {"message": "Workout Builder API. See /docs for Swagger UI."}


def create_app() -> FastAPI:
    """App factory returning the configured FastAPI instance.
    Kept for compatibility with test imports that access module-level `app`.
    """
    return app
