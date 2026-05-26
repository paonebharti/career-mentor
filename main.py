import asyncio
import os

from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse, Response
from app.dependencies import verify_api_key, check_rate_limit
from app.schemas import GoalRequest, EvaluationRequest, EvaluationResult, Roadmap
from app.agents.opportunities_agent import OpportunitiesAgent
from app.agents.notification_agent import NotificationAgent
from app.agents.evaluation_agent import EvaluationAgent
from app.services.roadmap_service import RoadmapService
from app.agents.calendar_agent import CalendarAgent
from app.agents.roadmap_agent import RoadmapAgent
from app.schemas import ReminderRequest
from app.logger import get_logger
from dotenv import load_dotenv
from typing import List

load_dotenv()
logger = get_logger("main")

app = FastAPI(
    title="Career Mentor",
    dependencies=[
        Depends(verify_api_key),
        Depends(check_rate_limit)
    ]
)

opportunities_agent = OpportunitiesAgent()
notification_agent = NotificationAgent()
evaluation_agent = EvaluationAgent()
roadmap_service = RoadmapService()
calendar_agent = CalendarAgent()
roadmap_agent = RoadmapAgent()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/mentor/evaluate/questions")
async def get_questions(request: GoalRequest):
    try:
        questions = await evaluation_agent.generate_questions(
            request.goal,
            request.background
        )
        return {"questions": questions}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/mentor/evaluate/answers")
async def evaluate_answers(request: EvaluationRequest):
    try:
        result = await evaluation_agent.evaluate_answers(
            request.goal,
            request.questions,
            request.answers
        )
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/mentor/roadmap")
async def generate_roadmap(goal: str, duration_days: int, request: EvaluationResult):
    try:
        roadmap = await roadmap_agent.generate_roadmap(goal, duration_days, request)
        roadmap_service.save(roadmap)
        return roadmap
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/mentor/calendar")
async def generate_calendar(roadmap: Roadmap):
    try:
        ics_bytes = calendar_agent.generate_calendar(roadmap)
        return Response(
            content=ics_bytes,
            media_type="text/calendar",
            headers={"Content-Disposition": "attachment; filename=roadmap.ics"}
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/mentor/opportunities")
async def find_opportunities(goal: str, request: EvaluationResult):
    try:
        result = await opportunities_agent.find_opportunities(goal, request)
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/mentor/remind")
async def send_reminder(request: ReminderRequest):
    try:
        roadmap = roadmap_service.get(request.roadmap_id)
        if not roadmap:
            return JSONResponse(status_code=404, content={"error": "Roadmap not found"})

        from datetime import date
        days_elapsed = (date.today() - request.start_date).days + 1
        today_plan = next(
            (d for d in roadmap.days if d.day == days_elapsed),
            None
        )

        if today_plan:
            subject = f"Career Mentor — Day {today_plan.day}: {today_plan.topic}"
            body = f"Hi! This is your daily Career Mentor reminder.\n\nDay {today_plan.day}: {today_plan.topic}\n\nStay consistent — you're making progress!"
            sms_message = f"Career Mentor: Day {today_plan.day} — {today_plan.topic}. Don't forget to study today!"
        else:
            subject = "Career Mentor Daily Reminder"
            body = "Hi! Don't forget to study today. Stay consistent!"
            sms_message = "Career Mentor: Don't forget to study today!"

        email_result, sms_result = await asyncio.gather(
            notification_agent.send_email(request.email, subject, body),
            notification_agent.send_sms(request.phone, sms_message)
        )

        return {"email": email_result, "sms": sms_result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
