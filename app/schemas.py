from pydantic import BaseModel
from typing import List
from datetime import time, date, datetime

class ChatRequest(BaseModel):
    session_id: str
    message: str

class DayPlan(BaseModel):
    day: int
    topic: str
    tasks: List[str]
    resources: List[str]

class Roadmap(BaseModel):
    id: str
    goal: str
    days: List[DayPlan]
    duration_days: int
    created_at: datetime

class EvaluationResult(BaseModel):
    strong_areas: List[str]
    weak_areas: List[str]
    focus_areas: List[str]
    experience_level: str
    summary: str

class ReminderRequest(BaseModel):
    email: str
    phone: str
    remind_at: time
    roadmap_id: str
    start_date: date
