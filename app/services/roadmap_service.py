import json
import os
from app.schemas import Roadmap
from app.logger import get_logger

logger = get_logger("roadmap_service")

class RoadmapService:
    def __init__(self, persist_path: str = "roadmaps.json"):
        self.persist_path = persist_path
        self.roadmaps: dict = {}
        self._load()

    def save(self, roadmap: Roadmap):
        self.roadmaps[roadmap.id] = roadmap.model_dump(mode="json")
        self._persist()
        logger.info(f"Roadmap saved: {roadmap.id}")

    def get(self, roadmap_id: str) -> Roadmap | None:
        data = self.roadmaps.get(roadmap_id)
        if not data:
            return None
        return Roadmap(**data)

    def _persist(self):
        with open(self.persist_path, "w") as f:
            json.dump(self.roadmaps, f, indent=2)

    def _load(self):
        if os.path.exists(self.persist_path):
            with open(self.persist_path, "r") as f:
                self.roadmaps = json.load(f)
            logger.info(f"Loaded {len(self.roadmaps)} roadmaps from disk")
