import asyncio
import json
import uuid
from datetime import datetime
from app.agents.base_agent import BaseAgent
from app.schemas import EvaluationResult, Roadmap, DayPlan
from app.logger import get_logger
from typing import List

logger = get_logger("roadmap_agent")

class RoadmapAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name = "RoadmapAgent",
            system_prompt = (
                "You are a roadmap specialist. "
                "You generate personalized day-wise learning roadmaps based on the user's goal and evaluation results. "
                "Each day should have a clear topic, practical tasks, and learning resources. "
                "Alternate between concept days, practice days, and revision days throughout the roadmap. "
                "Return ONLY valid JSON, no markdown, no explanation."
            ),
            tools = []
        )

    async def run(self, query: str) -> str:
        pass

    async def generate_roadmap(self, goal: str, duration_days: int, evaluation: EvaluationResult) -> Roadmap:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": (
                f"User goal: {goal}\nUser duration days: {duration_days}\nUser evaluation result: {evaluation.model_dump()}\n\n"
                "Generate roadmap for user to achieve the goal whithin duration days according to evaluation results. "
                "The roadmap should contain theory and practical tasks with levels like easy, medium and hard along with resources. "
                "Return ONLY a valid JSON array where each item has: day (int), topic (string), tasks (list of strings), resources (list of strings). No markdown, no explanation. "
            )}
        ]
        raw = await self._complete(messages, max_tokens=4000)
        print(f"RAW RESPONSE: {raw}")
        clean = raw.strip().replace("```json", "").replace("```", "").strip()
        # print("********************************************************************************************************************")
        # print(clean)
        # print("********************************************************************************************************************")
        day_plans = [DayPlan(**day) for day in json.loads(clean)]
        return Roadmap(
            id=str(uuid.uuid4()),
            goal=goal,
            duration_days=duration_days,
            days=day_plans,
            created_at=datetime.utcnow()
        )
