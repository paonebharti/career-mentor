import asyncio
import os
import uuid

from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse, Response
from app.dependencies import verify_api_key, check_rate_limit
from app.schemas import GoalRequest, EvaluationRequest, EvaluationResult, Roadmap, MentorRequest
from app.agents.opportunities_agent import OpportunitiesAgent
from app.agents.notification_agent import NotificationAgent
from app.agents.evaluation_agent import EvaluationAgent
from app.services.roadmap_service import RoadmapService
from app.services.session_service import SessionService
from app.agents.calendar_agent import CalendarAgent
from app.agents.roadmap_agent import RoadmapAgent
from app.agents.mentor_agent import MentorAgent
from app.schemas import ReminderRequest
from app.schemas import ChatRequest
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
session_service = SessionService()
calendar_agent = CalendarAgent()
roadmap_agent = RoadmapAgent()
mentor_agent = MentorAgent()

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

@app.post("/mentor/chat")
async def mentor_chat(request: ChatRequest):
    try:
        session = session_service.get(request.session_id)

        # new session
        if not session:
            session_service.create(request.session_id)
            session = session_service.get(request.session_id)

        phase = session["phase"]

        # phase 1 — extract goal details from prompt
        if phase == "extracting":
            goal_request = await mentor_agent.extract_goal(request.message)

            missing = []
            if not goal_request.goal:
                missing.append("goal")
            if not goal_request.background:
                missing.append("background")
            if not goal_request.duration_days:
                missing.append("duration in days or months")

            if missing:
                return {"reply": f"Could you also tell me your {', '.join(missing)}?"}

            session_service.update(
                request.session_id,
                goal=goal_request.goal,
                background=goal_request.background,
                duration_days=goal_request.duration_days
            )

            questions = await mentor_agent.evaluation_agent.generate_questions(
                goal_request.goal, goal_request.background
            )

            session_service.update(
                request.session_id,
                questions=questions,
                phase="questioning"
            )

            return {
                "reply": "Great! I have a few questions to assess your current knowledge.",
                "questions": questions
            }

        # phase 2 — user answered questions
        elif phase == "questioning":
            answers = [a.strip() for a in request.message.split("\n") if a.strip()]

            if len(answers) < len(session["questions"]):
                return {
                    "reply": f"Please answer all {len(session['questions'])} questions, one per line."
                }

            evaluation = await mentor_agent.evaluation_agent.evaluate_answers(
                session["goal"],
                session["questions"],
                answers
            )

            session_service.update(
                request.session_id,
                evaluation=evaluation.model_dump(),
                phase="generating"
            )

            session = session_service.get(request.session_id)

            from app.schemas import EvaluationResult
            eval_result = EvaluationResult(**session["evaluation"])

            roadmap, opportunities = await asyncio.gather(
                mentor_agent.roadmap_agent.generate_roadmap(
                    session["goal"], session["duration_days"], eval_result
                ),
                mentor_agent.opportunities_agent.find_opportunities(
                    session["goal"], eval_result
                )
            )

            calendar_bytes = mentor_agent.calendar_agent.generate_calendar(roadmap)
            mentor_agent.roadmap_service.save(roadmap)

            session_service.update(request.session_id, phase="complete")

            return {
                "reply": "Your personalized career roadmap is ready!",
                "evaluation": evaluation,
                "roadmap": roadmap,
                "opportunities": opportunities,
                "calendar": calendar_bytes.decode("utf-8")
            }

        elif phase == "complete":
            return {
                "reply": "Your roadmap is already generated. Use /mentor/remind to set up daily reminders.",
                "roadmap_id": session.get("roadmap_id")
            }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/mentor/start")
async def start_mentor(request: GoalRequest):
    try:
        questions = await mentor_agent.evaluation_agent.generate_questions(
            request.goal, request.background
        )
        return {"questions": questions}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/mentor/complete")
async def complete_mentor(request: MentorRequest):
    try:
        result = await mentor_agent.run(
            request.goal,
            request.background,
            request.duration_days,
            request.answers
        )
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
