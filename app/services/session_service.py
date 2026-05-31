from app.logger import get_logger

logger = get_logger("session_service")

class SessionService:
    def __init__(self):
        self.sessions: dict = {}

    def create(self, session_id: str):
        self.sessions[session_id] = {
            "phase": "extracting",
            "goal": None,
            "background": None,
            "duration_days": None,
            "questions": [],
            "evaluation": None,
            "roadmap_id": None
        }
        logger.info(f"Session created: {session_id}")

    def get(self, session_id: str) -> dict | None:
        return self.sessions.get(session_id)

    def update(self, session_id: str, **kwargs):
        if session_id in self.sessions:
            self.sessions[session_id].update(kwargs)
            logger.info(f"Session updated: {session_id} | {kwargs.keys()}")

    def delete(self, session_id: str):
        self.sessions.pop(session_id, None)
        logger.info(f"Session deleted: {session_id}")
