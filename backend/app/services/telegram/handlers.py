import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Optional, Set, Dict, Any, List
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models.water_body import WaterBody
from app.services.ai.service import AIService
from app.services.telegram.client import TelegramClient
from app.services.telegram.models import TelegramMessage, TelegramCallbackQuery
from app.services.telegram.intent_service import (
    TelegramIntentService,
    TelegramIntent,
    IntentResult,
)
from app.services.water_body_summary_service import (
    WaterBodySummaryService,
    WaterBodyTelegramSummary,
)

logger = logging.getLogger("jalnetra.services.telegram.handlers")


START_MESSAGE = """🌊 Welcome to JalNetra 2.0

I am your JalNetra water-body monitoring assistant.

You can ask me naturally in plain text:
• "Show Salim Ali Lake"
• "Give me the latest image of Salim Ali Lake"
• "Where is Chilika Lake?"
• "How is the water quality of Ooty Lake?"
• "How often does Salim Ali Lake change?"
• "List all water bodies"
• "How is Salim Ali Lake today?"

Commands:
/list — List registered water bodies
/waterbody <name> — Full telemetry & latest image
/status — Check system status
/ping — Bot connectivity check
/ai <question> — Ask AI Assistant
/help — Show commands & usage"""

HELP_MESSAGE = """🌊 JalNetra Helper

You can talk to me naturally or use commands:

Natural Language Examples:
• "Show Salim Ali Lake"
• "Give me the latest image of Salim Ali Lake"
• "Where is Salim Ali Lake?"
• "How is the water quality of Chilika Lake?"
• "How often does Salim Ali Lake change?"
• "Show all water bodies"
• "Tell me everything about Salim Ali Lake"

Available Commands:
/start — Start JalNetra Assistant
/help — Show available commands & guide
/ping — Check bot connectivity
/status — Check JalNetra services
/list — List available water bodies
/waterbody <name> — Show water-body information and latest stored image
/ai <question> — Ask the JalNetra AI Assistant

ℹ️ Water-body information is read directly from the JalNetra database and stored local observations."""

PING_MESSAGE = """🏓 JalNetra Telegram Bot is working.

Telegram API: OK
JalNetra Backend: OK"""


class TelegramCommandHandler:
    def __init__(
        self,
        client: TelegramClient,
        ai_service: Optional[AIService] = None,
        summary_service: Optional[WaterBodySummaryService] = None,
        db_factory: Optional[Callable] = None,
        intent_service: Optional[TelegramIntentService] = None,
    ):
        self.client = client
        self.ai_service = ai_service or AIService()
        self.summary_service = summary_service
        self._db_factory = db_factory
        self.intent_service = intent_service or TelegramIntentService(ai_service=self.ai_service)
        self._allowed_chat_ids: Optional[Set[str]] = self._parse_allowed_chat_ids()

    @contextmanager
    def _get_db(self):
        if self._db_factory:
            db = self._db_factory()
            try:
                yield db
            finally:
                db.close()
        else:
            with SessionLocal() as db:
                yield db

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
            with self._get_db() as db:
                db.execute(text("SELECT 1"))
            return "ONLINE"
        except Exception:
            return "OFFLINE"

    def _build_water_body_inline_keyboard(
        self, wb_id: str, google_maps_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Builds interactive Telegram inline keyboard for quick exploration."""
        row1: List[Dict[str, str]] = [
            {"text": "🛰 Latest Image", "callback_data": f"wb_img:{wb_id}"},
        ]
        if google_maps_url:
            row1.append({"text": "🗺 Open in Google Maps", "url": google_maps_url})

        row2: List[Dict[str, str]] = [
            {"text": "💧 Water Quality", "callback_data": f"wb_qual:{wb_id}"},
            {"text": "🌤 Weather", "callback_data": f"wb_weath:{wb_id}"},
            {"text": "📊 Monitoring", "callback_data": f"wb_mon:{wb_id}"},
        ]
        return {"inline_keyboard": [row1, row2]}

    async def _send_water_body_summary_and_photo(
        self,
        chat_id: int,
        service: WaterBodySummaryService,
        wb_id: str,
        is_today: bool = False,
    ):
        """Sends structured summary card with inline buttons and uploads latest photo if present."""
        summary = service.get_water_body_summary(wb_id)
        msg_text = service.format_telegram_summary_message(summary)

        if is_today:
            msg_text = "Based on the latest available JalNetra observation:\n\n" + msg_text

        keyboard = self._build_water_body_inline_keyboard(wb_id, summary.google_maps_url)
        await self.client.send_message(chat_id, msg_text, reply_markup=keyboard)

        # Upload photo if valid local image exists
        if summary.has_stored_visual_image and summary.latest_image_path:
            p = Path(summary.latest_image_path)
            if p.exists() and p.is_file():
                try:
                    photo_bytes = p.read_bytes()
                    caption = (
                        f"🛰 {summary.name} — Latest Visual\n\n"
                        f"Observation: {summary.latest_observation_date}\n"
                        f"Cloud Cover: {summary.cloud_cover}\n\n"
                        f"Latest stored visual observation available in JalNetra."
                    )
                    await self.client.send_photo(
                        chat_id=chat_id,
                        photo_bytes=photo_bytes,
                        filename=p.name,
                        caption=caption,
                    )
                except Exception as exc:
                    logger.warning("Failed to send latest visual observation photo: %s", exc)

    async def _send_photo_only(
        self,
        chat_id: int,
        service: WaterBodySummaryService,
        wb_id: str,
    ):
        """Specifically handles image-only requests (e.g. 'Show me the latest image of X')."""
        summary = service.get_water_body_summary(wb_id)

        if summary.has_stored_visual_image and summary.latest_image_path:
            p = Path(summary.latest_image_path)
            if p.exists() and p.is_file():
                try:
                    photo_bytes = p.read_bytes()
                    caption = (
                        f"🛰 {summary.name} — Latest Visual\n\n"
                        f"Observation: {summary.latest_observation_date}\n"
                        f"Cloud Cover: {summary.cloud_cover}\n\n"
                        f"Latest stored visual observation available in JalNetra."
                    )
                    await self.client.send_photo(
                        chat_id=chat_id,
                        photo_bytes=photo_bytes,
                        filename=p.name,
                        caption=caption,
                    )
                    return
                except Exception as exc:
                    logger.warning("Error reading/uploading photo for %s: %s", wb_id, exc)

        # Fallback explanation matching Section 23
        if summary.observation_count > 0:
            fallback = (
                f"🛰 Latest Visual — {summary.name}\n\n"
                f"Observation exists, image unavailable.\n\n"
                f"Available observations: {summary.observation_count}\n"
                f"The latest observation does not currently have a readable visual file."
            )
        else:
            fallback = (
                f"🛰 Latest Visual — {summary.name}\n\n"
                f"No visual observations have been fetched yet.\n"
                f"Use the JalNetra application to fetch visual observations first."
            )
        await self.client.send_message(chat_id, fallback)

    async def handle_callback_query(self, query: TelegramCallbackQuery):
        """Handles interactive inline button clicks."""
        chat_id = query.message.chat.id if query.message else (query.from_user.id if query.from_user else 0)
        data = query.data or ""
        logger.info("Handling callback query from chat %s: %s", chat_id, data)

        await self.client.answer_callback_query(query.id)

        if ":" not in data:
            return

        action, wb_id = data.split(":", 1)
        wb_id = wb_id.strip()

        with self._get_db() as db:
            service = self.summary_service or WaterBodySummaryService(db)
            try:
                summary = service.get_water_body_summary(wb_id)
            except Exception:
                await self.client.send_message(chat_id, "❌ Water body details not found.")
                return

            if action == "wb_img":
                await self._send_photo_only(chat_id, service, wb_id)

            elif action == "wb_qual":
                lines = [
                    f"💧 Water Quality — {summary.name}",
                    "",
                    f"Remote-Sensing Proxy: {summary.water_quality_label}",
                    "",
                    "Simple view:",
                    f'"{summary.water_quality_simple_text}"',
                    "",
                    "ℹ️ Remote-sensing optical proxies reflect visible clarity and spectral signatures. They do not substitute certified laboratory water testing.",
                ]
                await self.client.send_message(chat_id, "\n".join(lines))

            elif action == "wb_mon":
                lines = [
                    f"📊 Monitoring History — {summary.name}",
                    "",
                    f"Total Observations: {summary.observation_count}",
                ]
                if summary.monitoring_start and summary.monitoring_end:
                    lines.append(f"Period: {summary.monitoring_start} → {summary.monitoring_end}")
                lines.append(f"Frequency: {summary.observation_frequency}")
                lines.append(f"Latest Sensing: {summary.latest_observation_date}")
                lines.append(f"Cloud Cover: {summary.cloud_cover}")
                lines.append(f"Apparent Water Extent: {summary.apparent_water_extent}")
                await self.client.send_message(chat_id, "\n".join(lines))

            elif action == "wb_weath":
                await self._send_weather_summary(chat_id, db, wb_id)

    async def _send_weather_summary(self, chat_id: int, db: Session, wb_id: str):
        """Fetches and formats real-time Open-Meteo weather and rainfall-driven water-level trend for Telegram."""
        from app.services.weather import WeatherService, MissingCoordinatesError
        weather_svc = WeatherService(db)
        try:
            weather = await weather_svc.get_weather_for_water_body(wb_id)
            lines = [
                f"🌦 {weather.water_body_name}",
                "",
                "Current:",
                f"{weather.current.temperature_c:.1f}°C · {weather.current.condition}",
                "",
                "Rain today:",
                f"{weather.current.rain_mm:.1f} mm",
                "",
                "Next 7 days:",
                f"{weather.water_level_trend.forecast_rainfall_7d_mm:.1f} mm expected rainfall",
                "",
                "Water-level trend:",
                f"{weather.water_level_trend.trend_arrow} {weather.water_level_trend.trend_label}",
                "",
                "Reason:",
                weather.water_level_trend.reason,
                "",
                f"Confidence:\n{weather.water_level_trend.confidence.value}",
                "",
                "Note:\nWater-level trend is an environmental estimate, not a measured water-depth reading.",
            ]
            await self.client.send_message(chat_id, "\n".join(lines))
        except MissingCoordinatesError:
            await self.client.send_message(
                chat_id,
                "⚠️ Weather unavailable: This water body does not have valid coordinates.",
            )
        except Exception as exc:
            logger.warning("Weather fetch error for %s: %s", wb_id, exc)
            await self.client.send_message(
                chat_id,
                "⚠️ Weather data is temporarily unavailable from Open-Meteo.",
            )

    async def handle_message(self, message: TelegramMessage):
        """Processes incoming user text message (both slash commands and natural language)."""
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

        # 1. Check for slash commands (Preserve 100% backward compatibility)
        if raw_text.startswith("/"):
            parts = raw_text.split(maxsplit=1)
            command = parts[0].lower()
            if "@" in command:
                command = command.split("@")[0]
            args = parts[1].strip() if len(parts) > 1 else ""

            logger.info("Processing Telegram slash command from chat %s: '%s'", chat_id, command)

            if command == "/start":
                await self.client.send_message(chat_id, START_MESSAGE)
                return

            if command == "/help":
                await self.client.send_message(chat_id, HELP_MESSAGE)
                return

            if command == "/ping":
                await self.client.send_message(chat_id, PING_MESSAGE)
                return

            if command == "/status":
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
                return

            if command == "/list":
                with self._get_db() as db:
                    service = self.summary_service or WaterBodySummaryService(db)
                    wbs = service.list_water_bodies()
                    if not wbs:
                        await self.client.send_message(
                            chat_id,
                            "🌊 No water bodies are currently available in JalNetra.\n"
                            "Add a water body from the JalNetra application first.",
                        )
                        return
                    lines = ["🌊 JalNetra Water Bodies\n"]
                    for idx, wb in enumerate(wbs, start=1):
                        lines.append(f"{idx}. {wb.name}")
                    lines.append("\nReply with:\n/waterbody <name>\n\nExample:\n/waterbody " + wbs[0].name)
                    await self.client.send_message(chat_id, "\n".join(lines))
                    return

            if command == "/waterbody":
                if not args:
                    await self.client.send_message(
                        chat_id,
                        "Please specify a water body name.\nExample: /waterbody Chilika Lake\n\nUse /list to see all available water bodies.",
                    )
                    return

                with self._get_db() as db:
                    service = self.summary_service or WaterBodySummaryService(db)
                    matches = service.find_water_bodies(args)

                    if not matches:
                        await self.client.send_message(
                            chat_id,
                            "❌ Water body not found.\n\nUse /list to see the available water bodies.",
                        )
                        return

                    if len(matches) > 1:
                        lines = [f'I found multiple water bodies matching "{args}":\n']
                        for idx, wb in enumerate(matches, start=1):
                            lines.append(f"{idx}. {wb.name}")
                        lines.append(f"\nPlease use:\n/waterbody {matches[0].name}")
                        await self.client.send_message(chat_id, "\n".join(lines))
                        return

                    target_wb = matches[0]
                    self.intent_service.set_chat_context(chat_id, target_wb.id)
                    await self._send_water_body_summary_and_photo(chat_id, service, target_wb.id)
                    return

            if command == "/ai":
                if not args:
                    await self.client.send_message(
                        chat_id,
                        "Please provide a question after /ai.\nExample: /ai What is JalNetra?",
                    )
                    return

                # Read-only guard
                forbidden_keywords = [
                    "fetch satellite", "delete database", "run processing",
                    "execute command", "rm ", "drop table",
                ]
                if any(kw in args.lower() for kw in forbidden_keywords):
                    await self.client.send_message(
                        chat_id,
                        "⚠️ JalNetra AI is read-only in this version and cannot execute administrative server actions.",
                    )
                    return

                with self._get_db() as db:
                    service = self.summary_service or WaterBodySummaryService(db)
                    all_wbs = service.list_water_bodies()
                    matched_wb = None
                    for wb in all_wbs:
                        if wb.name.lower() in args.lower() or (wb.normalized_name and wb.normalized_name.lower() in args.lower()):
                            matched_wb = wb
                            break

                    if matched_wb:
                        self.intent_service.set_chat_context(chat_id, matched_wb.id)
                        ai_svc = self.ai_service
                        if getattr(ai_svc, "db", None) is None:
                            ai_svc.db = db
                        try:
                            res = ai_svc.generate_analysis_response(
                                water_body_id=matched_wb.id,
                                observation_id=None,
                                question=args,
                            )
                            reply = f"🤖 JalNetra AI — {matched_wb.name}\n\n{res.answer}"
                        except Exception as exc:
                            logger.warning("AI water body analysis error: %s", exc)
                            reply = f"🤖 JalNetra AI\n\n{self.ai_service.generate_general_response(args)}"
                    else:
                        ai_response = self.ai_service.generate_general_response(args)
                        reply = f"🤖 JalNetra AI\n\n{ai_response}"

                await self.client.send_message(chat_id, reply)
                return

        # 2. Natural Language Processing (Primary interaction mode)
        logger.info("Processing natural language query from chat %s: '%s'", chat_id, raw_text)

        with self._get_db() as db:
            service = self.summary_service or WaterBodySummaryService(db)
            all_wbs = service.list_water_bodies()

            intent_result: IntentResult = self.intent_service.classify_intent(
                text=raw_text,
                chat_id=chat_id,
                all_wbs=all_wbs,
            )

            intent = intent_result.intent
            target_wb = intent_result.water_body

            # Disambiguation needed
            if intent_result.water_body_candidates and len(intent_result.water_body_candidates) > 1:
                lines = [f'I found multiple possible water bodies:\n']
                for idx, wb in enumerate(intent_result.water_body_candidates, start=1):
                    lines.append(f"{idx}. {wb.name}")
                lines.append("\nWhich one would you like?")
                await self.client.send_message(chat_id, "\n".join(lines))
                return

            if intent == TelegramIntent.LIST_WATER_BODIES:
                if not all_wbs:
                    await self.client.send_message(
                        chat_id,
                        "🌊 No water bodies are currently available in JalNetra.\n"
                        "Add a water body from the JalNetra application first.",
                    )
                    return
                lines = ["🌊 Registered Water Bodies\n"]
                for idx, wb in enumerate(all_wbs, start=1):
                    lines.append(f"{idx}. {wb.name}")
                lines.append("\nAsk me about any water body, or type /waterbody <name>.")
                await self.client.send_message(chat_id, "\n".join(lines))
                return

            if intent == TelegramIntent.HELP:
                await self.client.send_message(chat_id, HELP_MESSAGE)
                return

            if intent == TelegramIntent.STATUS:
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
                return

            # For intents requiring a water body:
            if intent in (
                TelegramIntent.WATER_BODY_INFO,
                TelegramIntent.LATEST_IMAGE,
                TelegramIntent.LOCATION,
                TelegramIntent.WATER_QUALITY,
                TelegramIntent.WATER_EXTENT,
                TelegramIntent.MONITORING_FREQUENCY,
                TelegramIntent.WATER_VOLUME,
                TelegramIntent.WEATHER,
            ):
                if target_wb is None:
                    # Water body not specified and no context found
                    await self.client.send_message(
                        chat_id,
                        "Please specify which water body you'd like to check.\n"
                        "Example: \"Show Salim Ali Lake\" or \"Give me the latest image of Chilika Lake\".\n\n"
                        "Type /list to see all registered water bodies.",
                    )
                    return

                # Route to specific natural language response
                if intent == TelegramIntent.LATEST_IMAGE:
                    await self._send_photo_only(chat_id, service, target_wb.id)
                    return

                summary = service.get_water_body_summary(target_wb.id)

                if intent == TelegramIntent.LOCATION:
                    lines = [
                        f"📍 {summary.name}",
                        "",
                        summary.location,
                    ]
                    if summary.google_maps_url:
                        lines.extend([
                            "",
                            "🗺 Open in Google Maps",
                            summary.google_maps_url,
                        ])
                    keyboard = self._build_water_body_inline_keyboard(target_wb.id, summary.google_maps_url)
                    await self.client.send_message(chat_id, "\n".join(lines), reply_markup=keyboard)
                    return

                if intent == TelegramIntent.WATER_QUALITY:
                    lines = [
                        f"💧 Water Quality — {summary.name}",
                        "",
                        f"Remote-Sensing Proxy: {summary.water_quality_label}",
                        "",
                        "Simple view:",
                        f'"{summary.water_quality_simple_text}"',
                        "",
                        "ℹ️ Remote-sensing optical proxies reflect visible clarity and spectral signatures. They do not substitute certified laboratory water testing.",
                    ]
                    keyboard = self._build_water_body_inline_keyboard(target_wb.id, summary.google_maps_url)
                    await self.client.send_message(chat_id, "\n".join(lines), reply_markup=keyboard)
                    return

                if intent == TelegramIntent.WATER_EXTENT:
                    lines = [
                        f"📐 Water Extent & Surface Area — {summary.name}",
                        "",
                        f"Surface Area: {summary.surface_area_text}",
                        f"Latest Apparent Extent: {summary.apparent_water_extent}",
                        f"Latest Observation: {summary.latest_observation_date}",
                    ]
                    keyboard = self._build_water_body_inline_keyboard(target_wb.id, summary.google_maps_url)
                    await self.client.send_message(chat_id, "\n".join(lines), reply_markup=keyboard)
                    return

                if intent == TelegramIntent.MONITORING_FREQUENCY:
                    lines = [
                        f"🔄 Change & Monitoring Frequency — {summary.name}",
                        "",
                        f"Observed across {summary.observation_count} observation{'s' if summary.observation_count != 1 else ''}",
                    ]
                    if summary.monitoring_start and summary.monitoring_end:
                        lines.append(f"Period: {summary.monitoring_start} → {summary.monitoring_end}")
                    lines.append(f"Frequency: {summary.observation_frequency}")
                    lines.append(f"Latest Observation: {summary.latest_observation_date}")
                    keyboard = self._build_water_body_inline_keyboard(target_wb.id, summary.google_maps_url)
                    await self.client.send_message(chat_id, "\n".join(lines), reply_markup=keyboard)
                    return

                if intent == TelegramIntent.WATER_VOLUME:
                    lines = [
                        f"💧 Estimated Water Volume — {summary.name}",
                        "",
                        summary.water_volume,
                    ]
                    if summary.water_volume_note:
                        lines.extend(["", summary.water_volume_note])
                    keyboard = self._build_water_body_inline_keyboard(target_wb.id, summary.google_maps_url)
                    await self.client.send_message(chat_id, "\n".join(lines), reply_markup=keyboard)
                    return

                if intent == TelegramIntent.WEATHER:
                    await self._send_weather_summary(chat_id, db, target_wb.id)
                    return

                # WATER_BODY_INFO: send full summary card + photo
                await self._send_water_body_summary_and_photo(
                    chat_id, service, target_wb.id, is_today=intent_result.is_today_query
                )
                return

            if intent == TelegramIntent.AI_QUESTION:
                # Dispatch to AI Assistant
                if target_wb:
                    ai_svc = self.ai_service
                    if getattr(ai_svc, "db", None) is None:
                        ai_svc.db = db
                    try:
                        res = ai_svc.generate_analysis_response(
                            water_body_id=target_wb.id,
                            observation_id=None,
                            question=raw_text,
                        )
                        reply = f"🤖 JalNetra AI — {target_wb.name}\n\n{res.answer}"
                    except Exception as exc:
                        logger.warning("AI water body analysis error: %s", exc)
                        reply = f"🤖 JalNetra AI\n\n{self.ai_service.generate_general_response(raw_text)}"
                else:
                    reply = f"🤖 JalNetra AI\n\n{self.ai_service.generate_general_response(raw_text)}"

                await self.client.send_message(chat_id, reply)
                return

            # UNKNOWN intent fallback
            await self.client.send_message(
                chat_id,
                "I couldn't quite understand that. You can ask me naturally, such as:\n"
                "• \"Show Salim Ali Lake\"\n"
                "• \"Latest image of Chilika Lake\"\n"
                "• \"Where is Ooty Lake?\"\n"
                "• \"What is the water quality of Salim Ali Lake?\"\n"
                "• \"List all water bodies\"\n\n"
                "Or type /help for command options.",
            )
