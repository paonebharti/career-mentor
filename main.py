import asyncio
import os

from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from app.dependencies import verify_api_key, check_rate_limit
from app.schemas import ChatRequest, ReminderRequest
from app.agents.mentor_agent import MentorAgent
from app.services.roadmap_service import RoadmapService
from app.agents.notification_agent import NotificationAgent
from app.logger import get_logger
from dotenv import load_dotenv
from datetime import date

load_dotenv()
logger = get_logger("main")

app = FastAPI(
    title="Career Mentor",
    dependencies=[
        Depends(verify_api_key),
        Depends(check_rate_limit)
    ]
)

mentor_agent = MentorAgent()
roadmap_service = RoadmapService()
notification_agent = NotificationAgent()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ping")
def ping():
    return {"ping": "pong"}

@app.post("/mentor/chat")
async def mentor_chat(request: ChatRequest):
    try:
        result = await mentor_agent.chat(request.session_id, request.message)
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/mentor/remind")
async def send_reminder(request: ReminderRequest):
    try:
        roadmap = roadmap_service.get(request.roadmap_id)
        if not roadmap:
            return JSONResponse(status_code=404, content={"error": "Roadmap not found"})

        days_elapsed = (date.today() - request.start_date).days + 1
        today_plan = next(
            (d for d in roadmap.days if d.day == days_elapsed), None
        )

        if today_plan:
            subject = f"Career Mentor — Day {today_plan.day}: {today_plan.topic}"
            body = (
                f"Hi! This is your daily Career Mentor reminder.\n\n"
                f"Day {today_plan.day}: {today_plan.topic}\n\n"
                f"Stay consistent — you're making progress!"
            )
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
