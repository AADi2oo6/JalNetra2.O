import logging
from typing import Optional, Set
from sqlalchemy import text
from app.core.config import settings
from app.db.database import SessionLocal
from app.services.ai.service import AIService
from app.services.telegram.client import TelegramClient
from app.services.telegram.models import TelegramMessage

logger = logging.getLogger("jalnetra.services.telegram.handlers")


START_MESSAGE = """🌊 Welcome to JalNetra 2.0

I am the JalNetra monitoring assistant.

Current capabilities:
• Bot connectivity
• JalNetra AI connectivity
• Basic system status

Advanced satellite fetching, notifications and remote analysis will be enabled in future versions.

Use /help to see available commands."""

HELP_MESSAGE = """JalNetra 2.0 Commands

/start
Start the bot.

/help
Show available commands.

/ping
Test bot connectivity.

/status
Check JalNetra service status.

/ai <question>
Ask JalNetra AI a basic question."""

PING_MESSAGE = """🏓 JalNetra Telegram Bot is working.

Telegram API: OK
JalNetra Backend: OK"""


class TelegramCommandHandler:
    def __init__(self, client: TelegramClient, ai_service: Optional[AIService] = None):
        self.client = client
        self.ai_service = ai_service or AIService()
        self._allowed_chat_ids: Optional[Set[str]] = self._parse_allowed_chat_ids()

    def _parse_allowed_chat_ids(self) -> Optional[Set[str]]:
        raw = settings.TELEGRAM_ALLOWED_CHAT_IDS.strip()
        if not raw:
            return None
        ids = {cid.strip() for cid in raw.split(",") if cid.strip()}
        return ids if ids else None

    def is_chat_allowed(self, chat_id: int) -> bool:
        if self._allowed_chat_ids is None:
            return True
        return str(chat_id) in self._allowed_chat_ids

    def _check_db_status(self) -> str:
        try:
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
            return "ONLINE"
        except Exception:
            return "OFFLINE"

    async def handle_message(self, message: TelegramMessage):
        if not message.text:
            return

        chat_id = message.chat.id
        raw_text = message.text.strip()

        # Check authorization
        if not self.is_chat_allowed(chat_id):
            logger.warning("Rejected message from unauthorized Telegram chat ID: %s", chat_id)
            await self.client.send_message(
                chat_id, "🔒 Unauthorized access. Your chat ID is not permitted on this server."
            )
            return

        # Parse command
        parts = raw_text.split(maxsplit=1)
        command = parts[0].lower()
        # Handle command with bot mention (e.g. /start@jalNetra_Helperbot)
        if "@" in command:
            command = command.split("@")[0]

        args = parts[1].strip() if len(parts) > 1 else ""

        logger.info("Processing Telegram command '%s' from chat ID %s", command, chat_id)

        if command == "/start":
            await self.client.send_message(chat_id, START_MESSAGE)

        elif command == "/help":
            await self.client.send_message(chat_id, HELP_MESSAGE)

        elif command == "/ping":
            await self.client.send_message(chat_id, PING_MESSAGE)

        elif command == "/status":
            ai_status = self.ai_service.get_status()
            ai_label = "CONFIGURED" if ai_status.configured else "NOT CONFIGURED"
            db_label = self._check_db_status()

            status_msg = (
                "JalNetra Status\n\n"
                "Backend: ONLINE\n"
                f"AI: {ai_label}\n"
                "Telegram: CONNECTED\n"
                f"Database: {db_label}"
            )
            await self.client.send_message(chat_id, status_msg)

        elif command == "/ai":
            if not args:
                await self.client.send_message(
                    chat_id,
                    "Please provide a question after /ai.\nExample: /ai What is JalNetra?",
                )
                return

            # Read-only guard: explicitly reject server command attempts
            forbidden_keywords = ["fetch satellite", "delete database", "run processing", "execute command", "rm ", "drop table"]
            if any(kw in args.lower() for kw in forbidden_keywords):
                await self.client.send_message(
                    chat_id,
                    "⚠️ JalNetra AI is read-only in this version and cannot execute administrative server actions.",
                )
                return

            ai_response = self.ai_service.generate_general_response(args)
            reply = f"🤖 JalNetra AI\n\n{ai_response}"
            await self.client.send_message(chat_id, reply)

        else:
            # Friendly fallback for unhandled text
            await self.client.send_message(
                chat_id,
                "Unrecognized command. Type /help to see the available commands.",
            )
