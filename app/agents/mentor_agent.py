import asyncio
import json

from typing import List
from app.agents.base_agent import BaseAgent
from app.logger import get_logger

logger = get_logger("mentor_agent")

class MentorAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name = "MentorAgent",
            system_prompt = (
                "You are a Mentor who gives career guide. "
                "You have multiple other agents as well, use them whenever needed. "
                "Return ONLY valid JSON, no markdown."
            ),
            tools = []
        )

        from app.agents.evaluation_agent import EvaluationAgent
        from app.agents.roadmap_agent import RoadmapAgent
        from app.agents.opportunities_agent import OpportunitiesAgent
        from app.agents.calendar_agent import CalendarAgent
        from app.services.roadmap_service import RoadmapService
        from app.services.session_service import SessionService

        self.evaluation_agent = EvaluationAgent()
        self.roadmap_agent = RoadmapAgent()
        self.opportunities_agent = OpportunitiesAgent()
        self.calendar_agent = CalendarAgent()
        self.roadmap_service = RoadmapService()
        self.session_service = SessionService()


    async def run(self, goal: str, background: str, duration_days: int, answers: List[str]) -> dict:
        questions = await self.evaluation_agent.generate_questions(goal, background)
        evaluation = await self.evaluation_agent.evaluate_answers(goal, questions, answers)
        roadmap, opportunities = await asyncio.gather(
            self.roadmap_agent.generate_roadmap(goal, duration_days, evaluation),
            self.opportunities_agent.find_opportunities(goal, evaluation)
        )
        calendar_bytes = self.calendar_agent.generate_calendar(roadmap)
        self.roadmap_service.save(roadmap)

        return {
            "roadmap": roadmap,
            "opportunities": opportunities,
            "calendar": calendar_bytes.decode("utf-8"),
            "evaluation": evaluation
        }


    async def extract_goal(self, prompt: str) -> dict:
        messages = [
            {"role": "system", "content": (
                "Extract the user's career goal, background, and duration in days from their message. "
                "If duration is mentioned in months multiply by 30. "
                "If no duration is mentioned use 30 as default. "
                "Return ONLY a valid JSON object with fields: goal (string), background (string), duration_days (int). "
                "No markdown, no explanation."
            )},
            {"role": "user", "content": prompt}
        ]
        raw = await self._complete(messages)
        clean = raw.strip().replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean)
        return parsed


    async def chat(self, session_id: str, message: str) -> dict:
        session = self.session_service.get(session_id)

        if not session:
            self.session_service.create(session_id)
            session = self.session_service.get(session_id)

        phase = session["phase"]

        if phase == "extracting":
            return await self._handle_extracting(session_id, session, message)
        elif phase == "questioning":
            return await self._handle_questioning(session_id, session, message)
        elif phase == "complete":
            return await self._handle_complete(session_id, session, message)


    async def _handle_extracting(self, session_id: str, session: dict, message: str) -> dict:
        goal_request = await self.extract_goal(message)

        missing = []
        if not goal_request.get("goal"):
            missing.append("goal")
        if not goal_request.get("background"):
            missing.append("background and experience")
        if not goal_request.get("duration_days"):
            missing.append("duration in days or months")

        if missing:
            return {"reply": f"Could you also tell me your {', '.join(missing)}?"}

        self.session_service.update(
            session_id,
            goal=goal_request.get("goal"),
            background=goal_request.get("background"),
            duration_days=goal_request.get("duration_days")
        )

        questions = await self.evaluation_agent.generate_questions(
            goal_request.get("goal"), goal_request.get("background")
        )

        self.session_service.update(
            session_id,
            questions=questions,
            phase="questioning"
        )

        return {
            "reply": "Great! I have a few questions to assess your current knowledge level.",
            "questions": questions
        }


    async def _handle_questioning(self, session_id: str, session: dict, message: str) -> dict:
        answers = [a.strip() for a in message.split("\n") if a.strip()]

        if len(answers) < len(session["questions"]):
            return {
                "reply": f"Please answer all {len(session['questions'])} questions, one per line."
            }

        from app.schemas import EvaluationResult
        evaluation = await self.evaluation_agent.evaluate_answers(
            session["goal"],
            session["questions"],
            answers
        )

        self.session_service.update(
            session_id,
            evaluation=evaluation.model_dump(),
            phase="generating"
        )

        roadmap, opportunities = await asyncio.gather(
            self.roadmap_agent.generate_roadmap(
                session["goal"], session["duration_days"], evaluation
            ),
            self.opportunities_agent.find_opportunities(
                session["goal"], evaluation
            )
        )

        calendar_bytes = self.calendar_agent.generate_calendar(roadmap)
        self.roadmap_service.save(roadmap)

        self.session_service.update(
            session_id,
            roadmap_id=roadmap.id,
            phase="complete"
        )

        return {
            "reply": "Your personalized career roadmap is ready!",
            "evaluation": evaluation,
            "roadmap": roadmap,
            "opportunities": opportunities,
            "calendar": calendar_bytes.decode("utf-8")
        }


    async def _handle_complete(self, session_id: str, session: dict, message: str) -> dict:
        messages = [
            {"role": "system", "content": (
                f"You are a career mentor. The user has already generated their roadmap. "
                f"Their goal is: {session['goal']}. "
                f"Answer any follow-up questions they have about their roadmap or career path."
            )},
            {"role": "user", "content": message}
        ]
        reply = await self._complete(messages)
        return {
            "reply": reply,
            "roadmap_id": session.get("roadmap_id")
        }