from pydantic import BaseModel
from typing import Optional, List
from datetime import time, datetime

class GoalRequest (BaseModel):
    goal: str
    background: str
    duration_days: int

class ReminderRequest(BaseModel):
    email: str
    phone: str
    remind_at: time
    roadmap_id: str

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