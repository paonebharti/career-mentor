
import asyncio
import os

from app.agents.base_agent import BaseAgent
from app.logger import get_logger

logger = get_logger("notification_agent")

class NotificationAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name = "NotificationAgent",
            system_prompt = (
                "You are a reminder specialist. "
                "You send reminder to the user via email and sms on daily basis. "
                "You check the roadmap and send the reminder accordingly. "
            ),
            tools = []
        )

    async def run(self, query: str) -> str:
        pass

    async def send_email(self, to_email: str, subject: str, body: str) -> str:
        import resend
        resend.api_key = os.getenv("RESEND_API_KEY")
        
        response = await asyncio.to_thread(
            resend.Emails.send,
            {
                "from": "Career Mentor <onboarding@resend.dev>",
                "to": to_email,
                "subject": subject,
                "text": body
            }
        )
        
        logger.info(f"Email sent to {to_email}")
        return f"Email sent to {to_email}"

    async def send_sms(self, to_phone: str, message: str) -> str:
        from twilio.rest import Client
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        twilio_number = os.getenv("TWILIO_PHONE_NUMBER")

        client = Client(account_sid, auth_token)
        response = await asyncio.to_thread(
            lambda: client.messages.create(
                to=to_phone,
                from_=twilio_number,
                body=message
            )
        )

        logger.info(f"SMS sent to {to_phone}")
        return f"SMS sent to {to_phone}"
