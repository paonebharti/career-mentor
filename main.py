import os
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse, Response
from app.dependencies import verify_api_key, check_rate_limit
from app.schemas import GoalRequest, EvaluationRequest, EvaluationResult, Roadmap
from app.agents.evaluation_agent import EvaluationAgent
from app.agents.calendar_agent import CalendarAgent
from app.agents.roadmap_agent import RoadmapAgent
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

evaluation_agent = EvaluationAgent()
roadmap_agent = RoadmapAgent()
calendar_agent = CalendarAgent()

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
