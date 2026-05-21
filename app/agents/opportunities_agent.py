import asyncio
import json
from openai import AsyncOpenAI
from app.schemas import EvaluationResult
from app.agents.base_agent import BaseAgent
from app.logger import get_logger

logger = get_logger("opportunities_agent")

class OpportunitiesAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name = "OpportunitiesAgent",
            system_prompt = (
                "You are a opportunity search specialist. "
                "You search opportunities on the basis of skills and experience. "
                "You search open source projects relevant to users goal. "
                "You search communities to join relevant to goals and skills. "
            ),
            tools = []
        )

    async def run(self, query: str) -> str:
        pass

    async def find_opportunities(self, goal: str, evaluation: EvaluationResult) -> dict:
        from tavily import TavilyClient
        import os

        tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

        # run three searches concurrently
        job_search, project_search, community_search = await asyncio.gather(
            asyncio.to_thread(tavily.search, f"{goal} jobs for {evaluation.experience_level}"),
            asyncio.to_thread(tavily.search, f"open source projects for {goal}"),
            asyncio.to_thread(tavily.search, f"communities forums discord for {goal}")
        )

        # extract results
        jobs = [{"name": r["title"], "url": r["url"]} for r in job_search.get("results", [])]
        projects = [{"name": r["title"], "url": r["url"]} for r in project_search.get("results", [])]
        communities = [{"name": r["title"], "url": r["url"]} for r in community_search.get("results", [])]

        return {
            "jobs": jobs,
            "projects": projects,
            "communities": communities
        }
