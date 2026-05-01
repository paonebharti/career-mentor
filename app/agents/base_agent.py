import asyncio
from openai import AsyncOpenAI
from app.logger import get_logger

logger = get_logger("agent")

class BaseAgent:
    def __init__(self, name: str, system_prompt: str, tools: list = None):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools or []

    async def run(self, query: str) -> str:
        raise NotImplementedError("Each agent must implement run()")

    async def _complete(self, messages: list) -> str:
        try:
            client = AsyncOpenAI()
            kwargs = {
                "model": "gpt-4o-mini",
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 300
            }

            if self.tools:
                kwargs["tools"] = self.tools
                kwargs["tool_choice"] = "auto"

            response = await asyncio.wait_for(
                client.chat.completions.create(**kwargs),
                timeout=10
            )

            return response.choices[0].message.content

        except asyncio.TimeoutError:
            logger.error(f"{self.name} timed out")
            return f"{self.name} timed out"

        except Exception as e:
            logger.error(f"{self.name} failed: {str(e)}")
            return f"{self.name} failed: {str(e)}"
