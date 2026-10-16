"""
Unified Alert Event Bus for JalNetra 2.0.
Decouples alert production (IoT anomaly detector) from alert consumers (SSE streams, frontend floating toast, Telegram).
Provides async pub/sub queues for connected Server-Sent Events (SSE) clients.
"""
import asyncio
import logging
from typing import Any, Dict, Set, Tuple

logger = logging.getLogger("jalnetra.iot.event_bus")


class AlertEventBus:
    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    def subscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.add(queue)
        logger.debug("[EventBus] SSE client connected. Active SSE listeners: %d", len(self._subscribers))

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)
        logger.debug("[EventBus] SSE client disconnected. Active SSE listeners: %d", len(self._subscribers))

    def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Publish an event (e.g. 'iot_alert', 'session_stopped') to all connected SSE browser clients.
        """
        dead_queues = set()
        for q in list(self._subscribers):
            try:
                q.put_nowait((event_type, data))
            except asyncio.QueueFull:
                dead_queues.add(q)
            except Exception as e:
                logger.debug("[EventBus] Error publishing to client queue: %s", e)
                dead_queues.add(q)

        for dq in dead_queues:
            self._subscribers.discard(dq)


alert_event_bus = AlertEventBus()
