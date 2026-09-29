"""Request logging, bounded request bodies and per-process client rate limits."""

import logging
import math
from collections import OrderedDict
from time import monotonic
from uuid import uuid4

from starlette.responses import JSONResponse

from App.core.logging import correlation_id

logger = logging.getLogger("pokemon")
MAX_BODY_BYTES = 8192


class RateLimiter:
    def __init__(self, limit: int, clock=monotonic, capacity: int = 10000):
        self.limit, self.clock, self.capacity = limit, clock, capacity
        self.clients: OrderedDict[str, tuple[float, int]] = OrderedDict()

    def retry_after(self, client: str) -> int:
        now = self.clock()
        while self.clients and now - next(iter(self.clients.values()))[0] >= 60:
            self.clients.popitem(last=False)
        start, count = self.clients.get(client, (now, 0))
        if count >= self.limit or (client not in self.clients and len(self.clients) >= self.capacity):
            return max(1, math.ceil(60 - (now - start)))
        self.clients[client] = (start, count + 1)
        return 0


class OperationsMiddleware:
    def __init__(self, app, rate_limit: int):
        self.app = app
        self.limiter = RateLimiter(rate_limit)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        token = correlation_id.set(uuid4().hex)
        started = monotonic()
        request_path = scope["path"]
        status = 500
        response_started = False

        async def logged_send(message):
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                status = message["status"]
                response_started = True
                message.setdefault("headers", []).append((b"x-correlation-id", correlation_id.get().encode()))
            await send(message)

        async def reject(code, detail, headers=None):
            await JSONResponse({"detail": detail}, status_code=code, headers=headers)(scope, receive, logged_send)

        try:
            if scope["path"].startswith("/api/"):
                client = (scope.get("client") or ("unknown", 0))[0]
                retry = self.limiter.retry_after(client)
                if retry:
                    logger.warning("security_event", extra={"status": 429})
                    return await reject(429, "Too many requests", {"Retry-After": str(retry)})
                body = bytearray()
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    chunk = message.get("body", b"")
                    if len(body) + len(chunk) > MAX_BODY_BYTES:
                        return await reject(413, "Request body too large")
                    body.extend(chunk)
                    if not message.get("more_body", False):
                        break
                sent = False

                async def replay():
                    nonlocal sent
                    if not sent:
                        sent = True
                        return {"type": "http.request", "body": bytes(body), "more_body": False}
                    return await receive()

                await self.app(scope, replay, logged_send)
            else:
                await self.app(scope, receive, logged_send)
        except Exception:
            logger.exception("internal_error")
            if response_started:
                raise
            await reject(500, "Internal server error")
        finally:
            # Log the route template, never arbitrary user input in URL paths.
            route = scope.get("route")
            endpoint = request_path if request_path in {
                "/api/v1/analyze", "/health", "/ready", "/docs", "/openapi.json", "/redoc"
            } else getattr(route, "path", "unmatched")
            logger.info("request", extra={
                "endpoint": endpoint, "status": status,
                "request_count": 1, "request_duration_ms": round((monotonic() - started) * 1000, 2),
            })
            correlation_id.reset(token)
