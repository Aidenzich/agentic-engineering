import asyncio
from collections import defaultdict
from typing import Any, Callable, Coroutine

EventHandler = Callable[..., Coroutine[Any, Any, None]]


class EventBus:
    """Lightweight in-process async event bus. Sufficient for Phase 1; can be replaced with Redis Streams in Phase 2+."""

    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def on(self, event: str, handler: EventHandler) -> None:
        """Register an event handler."""
        self._handlers[event].append(handler)

    async def emit(self, event: str, **kwargs) -> None:
        """Emit an event. All handlers execute concurrently (fire-and-forget, non-blocking)."""
        handlers = self._handlers.get(event, [])
        if handlers:
            await asyncio.gather(
                *(h(**kwargs) for h in handlers),
                return_exceptions=True,
            )


event_bus = EventBus()
