"""Cross-cutting middleware: structured logging, request IDs, rate limiting."""
import logging
import sys
import time
import uuid
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .config import settings

logger = logging.getLogger("chancery")


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        '{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
    ))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request id and log one structured line per request."""
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id", uuid.uuid4().hex[:12])
        start = time.perf_counter()
        request.state.request_id = rid
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("unhandled error rid=%s path=%s", rid, request.url.path)
            return JSONResponse({"detail": "Internal server error", "request_id": rid}, status_code=500)
        dur = (time.perf_counter() - start) * 1000
        logger.info("rid=%s %s %s -> %s %.1fms",
                    rid, request.method, request.url.path, response.status_code, dur)
        response.headers["x-request-id"] = rid
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory per-IP sliding window. Swap for Redis in multi-instance prod."""
    def __init__(self, app):
        super().__init__(app)
        self.hits: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api"):
            ip = request.client.host if request.client else "unknown"
            now = time.time()
            window = settings.rate_limit_window_seconds
            q = self.hits[ip]
            while q and q[0] < now - window:
                q.popleft()
            if len(q) >= settings.rate_limit_requests:
                return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
            q.append(now)
        return await call_next(request)
