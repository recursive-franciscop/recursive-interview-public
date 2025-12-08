from typing import List, Optional
from pydantic import BaseModel, Field


# Domain models
class Exercise(BaseModel):
    id: int
    name: str
    muscle_group: str
    equipment: Optional[str] = None
    type: str = "strength"  # strength | cardio | mobility


class WorkoutItem(BaseModel):
    exercise_id: int
    sets: Optional[int] = Field(default=None, ge=1)
    reps: Optional[int] = Field(default=None, ge=1)
    duration_seconds: Optional[int] = Field(default=None, ge=1)
    notes: Optional[str] = None


class Workout(BaseModel):
    id: int
    name: str
    items: List[WorkoutItem]


class WorkoutCreate(BaseModel):
    name: str
    items: List[WorkoutItem]


# AI Types
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    prompt: Optional[str] = None
    messages: Optional[List[ChatMessage]] = None
    model: Optional[str] = None
    temperature: Optional[float] = 0.7


class ChatResult(BaseModel):
    reply: str
    model: str

# -------------------------
# AI Workout Planning (structured outputs)
# -------------------------
class RawTargetMuscleGroups(BaseModel):
    primary: list[str] = []
    secondary: list[str] = []


class RawExercise(BaseModel):
    exercise_id: int
    name: str
    equipment_type: Optional[str] = None
    target_muscle_groups: RawTargetMuscleGroups
    utility: Optional[str] = None


class AIWorkoutItemSuggestion(BaseModel):
    exercise: RawExercise
    prescription: WorkoutItem  # sets/reps for strength OR duration_seconds for cardio/mobility


class AIWorkoutPlan(BaseModel):
    name: str
    items: list[AIWorkoutItemSuggestion]

# Multi-day program
class AIWorkoutDay(BaseModel):
    name: str
    items: list[AIWorkoutItemSuggestion]

class AIWorkoutProgram(BaseModel):
    name: str
    days: list[AIWorkoutDay]
    suggestions: Optional[list[AIWorkoutItemSuggestion]] = None
