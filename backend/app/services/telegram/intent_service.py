import json
import logging
import re
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple, Any
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.water_body import WaterBody
from app.services.ai.service import AIService

logger = logging.getLogger("jalnetra.services.telegram.intent")


class TelegramIntent(str, Enum):
    LIST_WATER_BODIES = "LIST_WATER_BODIES"
    WATER_BODY_INFO = "WATER_BODY_INFO"
    LATEST_IMAGE = "LATEST_IMAGE"
    LOCATION = "LOCATION"
    WATER_QUALITY = "WATER_QUALITY"
    WATER_EXTENT = "WATER_EXTENT"
    MONITORING_FREQUENCY = "MONITORING_FREQUENCY"
    WATER_VOLUME = "WATER_VOLUME"
    WEATHER = "WEATHER"
    HELP = "HELP"
    STATUS = "STATUS"
    AI_QUESTION = "AI_QUESTION"
    UNKNOWN = "UNKNOWN"


@dataclass
class IntentResult:
    intent: TelegramIntent
    water_body: Optional[WaterBody] = None
    water_body_candidates: Optional[List[WaterBody]] = None
    raw_query: str = ""
    is_today_query: bool = False
    context_used: bool = False


# Generic water body stopwords that should not match a lake by themselves
GENERIC_WATER_TERMS = {
    "lake", "lakes", "reservoir", "reservoirs", "dam", "dams",
    "water", "waterbody", "waterbodies", "body", "pond", "ponds",
    "river", "rivers", "sea", "lagoon", "wetland", "the", "a", "an",
}


class TelegramIntentService:
    """
    Deterministic intent and entity classification engine for JalNetra Telegram Bot,
    with conversational context tracking and secure structured OpenAI fallback.
    """

    def __init__(self, ai_service: Optional[AIService] = None):
        self.ai_service = ai_service or AIService()
        # In-memory conversational context: chat_id -> last_water_body_id
        self._chat_context: Dict[int, str] = {}

    def get_chat_context(self, chat_id: int) -> Optional[str]:
        return self._chat_context.get(chat_id)

    def set_chat_context(self, chat_id: int, water_body_id: str):
        self._chat_context[chat_id] = water_body_id

    def clear_chat_context(self, chat_id: int):
        self._chat_context.pop(chat_id, None)

    def _find_water_body_entities(
        self, text: str, all_wbs: List[WaterBody]
    ) -> List[WaterBody]:
        """
        Extracts candidate water bodies mentioned in user text using exact,
        substring, and token-based fuzzy matching.
        """
        clean_text = text.lower().strip()
        # Remove common punctuation
        clean_text_words = set(re.findall(r"\b\w+\b", clean_text))

        # 1. Exact match against full name or normalized name
        for wb in all_wbs:
            wb_name = (wb.name or "").strip().lower()
            wb_norm = (wb.normalized_name or "").strip().lower()
            if wb_name and wb_name == clean_text:
                return [wb]
            if wb_norm and wb_norm == clean_text:
                return [wb]

        # 2. Full name substring inside user text (e.g. "show salim ali lake please")
        exact_substring_matches = []
        for wb in all_wbs:
            wb_name = (wb.name or "").strip().lower()
            wb_norm = (wb.normalized_name or "").strip().lower()
            if wb_name and wb_name in clean_text:
                exact_substring_matches.append(wb)
            elif wb_norm and wb_norm in clean_text:
                exact_substring_matches.append(wb)

        if exact_substring_matches:
            # Prefer longest matching name if multiple match
            exact_substring_matches.sort(key=lambda w: len(w.name or ""), reverse=True)
            return exact_substring_matches

        # 3. Specific distinctive tokens (e.g. "salim ali" for "Salim Ali Lake", "ooty" for "Ooty Lake")
        token_matches = []
        for wb in all_wbs:
            wb_name = (wb.name or "").strip().lower()
            wb_tokens = set(re.findall(r"\b\w+\b", wb_name))
            distinctive_tokens = wb_tokens - GENERIC_WATER_TERMS
            if not distinctive_tokens:
                distinctive_tokens = wb_tokens

            # Check if all distinctive tokens of this lake appear in user text
            if distinctive_tokens and distinctive_tokens.issubset(clean_text_words):
                token_matches.append(wb)
            # Or if any distinctive multi-character token >= 4 letters appears
            elif any(tok in clean_text_words and len(tok) >= 4 for tok in distinctive_tokens):
                token_matches.append(wb)

        # Remove duplicates while preserving order
        seen = set()
        unique_matches = []
        for wb in token_matches:
            if wb.id not in seen:
                seen.add(wb.id)
                unique_matches.append(wb)

        return unique_matches

    def classify_intent(
        self,
        text: str,
        chat_id: int,
        all_wbs: List[WaterBody],
    ) -> IntentResult:
        """
        Main natural-language classifier.
        Uses deterministic keyword/entity rules first.
        Falls back to structured OpenAI classification only for ambiguous inputs.
        """
        raw = text.strip()
        lower = raw.lower()

        # Check for "today" phrasing
        is_today = bool(re.search(r"\btoday\b", lower))

        # 1. High-priority commands & greetings / help / status
        if lower in ("/start", "start", "hi", "hello", "hey"):
            return IntentResult(intent=TelegramIntent.HELP, raw_query=raw)

        if lower in ("/help", "help", "guide", "commands", "how to use"):
            return IntentResult(intent=TelegramIntent.HELP, raw_query=raw)

        if lower in ("/ping", "ping", "/status", "status", "health"):
            return IntentResult(intent=TelegramIntent.STATUS, raw_query=raw)

        # 2. List all water bodies
        list_patterns = [
            r"\b(list|all)\b.*\b(water|lakes?|reservoirs?|bodies)\b",
            r"\b(show|get|view)\b.*\b(all)\b",
            r"\bwhat\b.*\b(water\s*bodies|lakes)\b.*\b(do\s*you\s*have|available)\b",
            r"^/list$",
            r"^list$",
            r"^all water bodies$",
            r"^show all$",
        ]
        if any(re.search(pat, lower) for pat in list_patterns):
            return IntentResult(intent=TelegramIntent.LIST_WATER_BODIES, raw_query=raw)

        # 3. Entity detection
        matched_wbs = self._find_water_body_entities(raw, all_wbs)

        target_wb: Optional[WaterBody] = None
        context_used = False

        if len(matched_wbs) == 1:
            target_wb = matched_wbs[0]
            # Save context for future follow-ups
            self.set_chat_context(chat_id, target_wb.id)
        elif len(matched_wbs) > 1:
            # Multiple matches -> Disambiguation
            return IntentResult(
                intent=TelegramIntent.WATER_BODY_INFO,
                water_body_candidates=matched_wbs,
                raw_query=raw,
            )
        else:
            # No registered water body matched in text.
            # Check if user explicitly named another water body (e.g. "Chilika Lake", "Pichola Reservoir")
            # If they named an explicit entity not in our DB, do NOT fallback to the previous context.
            named_lake_match = re.search(
                r"\b([a-zA-Z0-9\-\'\s]{2,})\s+(lake|reservoir|dam|pond|talab|wetland|water\s*body)\b",
                lower,
            )
            is_explicit_unregistered_entity = False
            if named_lake_match:
                prefix = named_lake_match.group(1).strip()
                prefix_words = set(prefix.split()) - {"the", "a", "an", "this", "that", "its", "our"}
                if prefix_words:
                    is_explicit_unregistered_entity = True

            stored_id = self.get_chat_context(chat_id)
            if stored_id and not is_explicit_unregistered_entity:
                for wb in all_wbs:
                    if wb.id == stored_id:
                        target_wb = wb
                        context_used = True
                        break

        # 4. Deterministic Intent Detection based on Keywords
        # A. Latest visual image
        image_keywords = ["image", "photo", "picture", "visual", "satellite", "look like", "satellite view", "satellite image"]
        if any(kw in lower for kw in image_keywords):
            return IntentResult(
                intent=TelegramIntent.LATEST_IMAGE,
                water_body=target_wb,
                raw_query=raw,
                is_today_query=is_today,
                context_used=context_used,
            )

        # B. Location / Google Maps
        location_keywords = ["where is", "where's", "where", "location", "locate", "map", "maps", "coordinates", "situated", "directions"]
        if any(re.search(r"\b" + re.escape(kw) + r"\b", lower) for kw in location_keywords):
            return IntentResult(
                intent=TelegramIntent.LOCATION,
                water_body=target_wb,
                raw_query=raw,
                is_today_query=is_today,
                context_used=context_used,
            )

        # C. Water Quality
        quality_keywords = [
            "water quality", "quality", "clean", "dirty", "clarity", "clear",
            "algae", "turbid", "turbidity", "drinking", "potable", "safe to drink",
            "how is the water", "water condition", "condition of the water",
        ]
        if any(re.search(r"\b" + re.escape(kw) + r"\b", lower) for kw in quality_keywords):
            return IntentResult(
                intent=TelegramIntent.WATER_QUALITY,
                water_body=target_wb,
                raw_query=raw,
                is_today_query=is_today,
                context_used=context_used,
            )

        # D. Water Extent / Surface Area
        extent_keywords = ["surface area", "water extent", "how big", "area of", "extent of", "size"]
        if any(re.search(r"\b" + re.escape(kw) + r"\b", lower) for kw in extent_keywords):
            return IntentResult(
                intent=TelegramIntent.WATER_EXTENT,
                water_body=target_wb,
                raw_query=raw,
                is_today_query=is_today,
                context_used=context_used,
            )

        # E. Change / Monitoring Frequency
        freq_keywords = ["how often", "frequency", "change", "changes", "monitoring", "monitored", "how frequently", "observations", "observation history"]
        if any(re.search(r"\b" + re.escape(kw) + r"\b", lower) for kw in freq_keywords):
            return IntentResult(
                intent=TelegramIntent.MONITORING_FREQUENCY,
                water_body=target_wb,
                raw_query=raw,
                is_today_query=is_today,
                context_used=context_used,
            )

        # F. Water Volume
        volume_keywords = ["volume", "how much water", "capacity", "water amount", "depth", "deep"]
        if any(re.search(r"\b" + re.escape(kw) + r"\b", lower) for kw in volume_keywords):
            return IntentResult(
                intent=TelegramIntent.WATER_VOLUME,
                water_body=target_wb,
                raw_query=raw,
                is_today_query=is_today,
                context_used=context_used,
            )

        # G. Weather / Climate (Phase 6 placeholder)
        weather_keywords = ["weather", "temperature", "forecast", "rain", "rainfall", "climate", "hot", "cold"]
        if any(re.search(r"\b" + re.escape(kw) + r"\b", lower) for kw in weather_keywords):
            return IntentResult(
                intent=TelegramIntent.WEATHER,
                water_body=target_wb,
                raw_query=raw,
                is_today_query=is_today,
                context_used=context_used,
            )

        # H. If a water body was recognized and user said "Show X", "Tell me about X", "How is X today?", "Give me everything about X"
        if target_wb is not None:
            return IntentResult(
                intent=TelegramIntent.WATER_BODY_INFO,
                water_body=target_wb,
                raw_query=raw,
                is_today_query=is_today,
                context_used=context_used,
            )

        # 5. Fallback: If configured with AI and query looks conversational/questioning
        if self.ai_service and getattr(self.ai_service, "is_configured", False) and ("?" in lower or len(lower.split()) > 2):
            ai_structured = self._classify_with_openai(raw, [w.name for w in all_wbs if w.name])
            if ai_structured:
                intent_enum = getattr(TelegramIntent, ai_structured.get("intent", "AI_QUESTION"), TelegramIntent.AI_QUESTION)
                wb_name = ai_structured.get("water_body_name")
                found_wb = None
                if wb_name:
                    for wb in all_wbs:
                        if wb.name.lower() == wb_name.lower():
                            found_wb = wb
                            self.set_chat_context(chat_id, wb.id)
                            break
                return IntentResult(
                    intent=intent_enum,
                    water_body=found_wb or target_wb,
                    raw_query=raw,
                    is_today_query=is_today,
                    context_used=context_used,
                )

        # 6. Default to AI question if it has a question mark or general conversational phrase
        if "?" in lower or lower.startswith(("what", "why", "how", "tell", "explain")):
            return IntentResult(
                intent=TelegramIntent.AI_QUESTION,
                water_body=target_wb,
                raw_query=raw,
                is_today_query=is_today,
                context_used=context_used,
            )

        return IntentResult(
            intent=TelegramIntent.UNKNOWN,
            water_body=target_wb,
            raw_query=raw,
            is_today_query=is_today,
            context_used=context_used,
        )

    def _classify_with_openai(self, text: str, available_names: List[str]) -> Optional[Dict[str, Any]]:
        """
        Uses OpenAI to classify intent strictly into structured JSON.
        Never executes code or mutations.
        """
        try:
            client = getattr(self.ai_service, "client", None)
            if not client:
                return None

            prompt = (
                "You are an intent classifier for a water-body monitoring system.\n"
                f"Available water bodies: {', '.join(available_names[:30])}\n\n"
                "Classify the user message into one of these intents:\n"
                "LIST_WATER_BODIES, WATER_BODY_INFO, LATEST_IMAGE, LOCATION, WATER_QUALITY, "
                "WATER_EXTENT, MONITORING_FREQUENCY, WATER_VOLUME, WEATHER, HELP, STATUS, AI_QUESTION.\n\n"
                "Return strictly a JSON object with keys:\n"
                "{\n"
                '  "intent": "<INTENT_NAME>",\n'
                '  "water_body_name": "<matched water body name or null>"\n'
                "}\n\n"
                f'User message: "{text}"'
            )

            res = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=100,
                response_format={"type": "json_object"},
            )
            content = res.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.debug("OpenAI intent classification skipped/failed: %s", e)
            return None
