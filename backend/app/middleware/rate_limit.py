from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Small in-memory limiter for the demo's public mutation endpoints."""

    def __init__(self, app, chat_limit: int = 120, login_limit: int = 10):
        super().__init__(app)
        self.chat_limit = max(1, chat_limit)
        self.login_limit = max(1, login_limit)
        self.window_seconds = 60.0
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    async def dispatch(self, request: Request, call_next):
        limit = self._limit_for(request)
        if limit is None:
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        key = f"{client_host}:{request.url.path}"
        now = monotonic()
        with self._lock:
            events = self._events[key]
            cutoff = now - self.window_seconds
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, round(self.window_seconds - (now - events[0])))
                return JSONResponse(
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                    content={
                        "success": False,
                        "message": "Bạn đang gửi yêu cầu quá nhanh. Vui lòng thử lại sau.",
                        "data": None,
                    },
                )
            events.append(now)

            # Avoid retaining inactive client keys forever in a long-running process.
            if len(self._events) > 10_000:
                stale_keys = [
                    stored_key
                    for stored_key, stored_events in self._events.items()
                    if not stored_events or stored_events[-1] <= cutoff
                ]
                for stale_key in stale_keys:
                    self._events.pop(stale_key, None)

        return await call_next(request)

    def _limit_for(self, request: Request) -> int | None:
        if request.method != "POST":
            return None
        if request.url.path == "/api/auth/login":
            return self.login_limit
        if request.url.path in {"/api/chat/sessions", "/api/chat/messages"}:
            return self.chat_limit
        return None
