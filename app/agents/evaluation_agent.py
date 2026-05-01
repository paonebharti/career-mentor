import asyncio
import json
from app.agents.base_agent import BaseAgent
from app.schemas import EvaluationResult
from app.logger import get_logger
from typing import List

logger = get_logger("evaluation_agent")

class EvaluationAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name = "EvaluationAgent",
            system_prompt = (
                "You are a evaluation specialist. "
                "You ONLY ask questions and evaluate answers on the basis of users goal. "
                "These questions should be related to users goal to evaluate their knowledge base on the goals. "
                "You evaluate the users answers and give feedback on thier weak and strong areas for that particular goal. "
            ),
            tools = []
        )

    async def run(self, query: str) -> str:
        pass

    async def generate_questions(self, goal: str, background: str) -> list[str]:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": (
                f"User goal: {goal}\nUser background: {background}\n\n"
                "Generate five questions to evaluate the user's knowledge base, weak and strong spots, and areas to focus on. "
                "If the user's goal and background align, increase the difficulty of the questions. "
                "Return ONLY a JSON array of five strings, no markdown, no explanation."
            )}
        ]

        raw = await self._complete(messages)
        clean = raw.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
        
    async def evaluate_answers(self, goal: str, questions: List[str], answers: List[str]) -> EvaluationResult:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": (
                f"User goal: {goal}\nQuestions asked: {questions}\nUser answers: {answers}\n\n"
                "Evaluate the answers given by user for the questions asked. "
                "On the basis of evaluated answers and background give detailed feedback adding user's weak, strong spots and areas to focus on. "
                "Return ONLY a valid JSON object with fields: strong_areas (list), weak_areas (list), focus_areas (list), experience_level (string: beginner/intermediate/advanced), summary (string). No markdown, no explanation."
            )}
        ]

        raw = await self._complete(messages)
        clean = raw.strip().replace("```json", "").replace("```", "").strip()
        return EvaluationResult(**json.loads(clean))
