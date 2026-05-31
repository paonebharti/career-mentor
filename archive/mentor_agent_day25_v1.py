import asyncio
import json

from typing import List
from app.agents.base_agent import BaseAgent
from app.schemas import GoalRequest
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

        self.evaluation_agent = EvaluationAgent()
        self.roadmap_agent = RoadmapAgent()
        self.opportunities_agent = OpportunitiesAgent()
        self.calendar_agent = CalendarAgent()
        self.roadmap_service = RoadmapService()

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

    async def extract_goal(self, prompt: str) -> GoalRequest:
        messages = [
            {"role": "system", "content": (
                "Extract the user's career goal, background, and duration in days from their message. "
                "If duration is mentioned in months multiply by 30. "
                "If no duration is mentioned use 90 as default. "
                "Return ONLY a valid JSON object with fields: goal (string), background (string), duration_days (int). "
                "No markdown, no explanation."
            )},
            {"role": "user", "content": prompt}
        ]
        raw = await self._complete(messages)
        clean = raw.strip().replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean)
        return GoalRequest(**parsed)
