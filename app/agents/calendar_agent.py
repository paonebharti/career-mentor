from app.agents.base_agent import BaseAgent
from icalendar import Calendar, Event
from datetime import datetime, timedelta
from app.schemas import Roadmap
from app.logger import get_logger

logger = get_logger("calendar_agent")

class CalendarAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name = "CalendarAgent",
            system_prompt = (
                "You are a calendar specialist. "
                "You ONLY generate .ics file with day-by-day plan. "
            ),
            tools = []
        )

    def run(self, query: str) -> str:
        pass

    def generate_calendar(self, roadmap: Roadmap) -> bytes:
        cal = Calendar()
        cal.add('prodid', '-//Career Mentor//EN')
        cal.add('version', '2.0')

        start_date = roadmap.created_at.date()

        for day_plan in roadmap.days:
            event = Event()
            event_date = start_date + timedelta(days=day_plan.day - 1)
            
            event.add('summary', f"Day {day_plan.day}: {day_plan.topic}")  # ← day number and topic
            event.add('description', "Tasks:\n" + "\n".join(day_plan.tasks) + "\n\nResources:\n" + "\n".join(day_plan.resources))  # ← tasks and resources as a string
            event.add('dtstart', event_date)
            event.add('dtend', event_date + timedelta(hours=2))
            
            cal.add_component(event)

        return cal.to_ical()
