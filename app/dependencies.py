import os
import time
from collections import defaultdict
from fastapi import Header, HTTPException
from app.logger import get_logger

logger = get_logger("dependencies")


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        window_start = now - self.window_seconds

        self.requests[client_id] = [
            ts for ts in self.requests[client_id]
            if ts > window_start
        ]

        if len(self.requests[client_id]) >= self.max_requests:
            return False

        self.requests[client_id].append(now)
        return True


rate_limiter = RateLimiter(max_requests=10, window_seconds=60)

async def verify_api_key(x_api_key: str = Header()):
    key = os.getenv("AGENT_API_KEY")
    
    if not key:
        logger.error("AGENT_API_KEY not set in environment")
        raise HTTPException(status_code=500, detail="Server misconfiguration")

    if x_api_key != key:
        logger.warning(f"Invalid API key attempt: {x_api_key[:6]}...")
        raise HTTPException(status_code=401, detail="Invalid API key")

async def check_rate_limit(x_api_key: str = Header()):
    if not rate_limiter.is_allowed(x_api_key):
        logger.warning(f"Rate limit exceeded for key: {x_api_key[:6]}...")
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Max 10 requests per minute."
        )
