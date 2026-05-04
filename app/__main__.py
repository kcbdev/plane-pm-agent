"""HTTP mode entry point for plane-pm-agent.

Hardening layers:
1. API key auth — X-API-Key or Authorization: Bearer header.
2. Rate limiting — sliding window, configurable limit (default 60 req/min per IP).
3. Security headers — HSTS, CSP, X-Frame-Options, no-sniff, etc.
"""
from __future__ import annotations

import os
import re
import secrets
import sys
import time
from collections import defaultdict
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from uvicorn.config import Config
from uvicorn.server import Server

from app import mcp


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
AUTH_ENABLED = os.getenv("PM_AGENT_AUTH_ENABLED", "true").lower() in ("1", "true", "yes")
AUTH_KEY = os.getenv("PM_AGENT_API_KEY", "")

# Rate limiting: "60/minute" → (count, seconds). Default 60 req / 60 s per IP.
RATE_LIMIT_STR = os.getenv("PM_AGENT_RATE_LIMIT", "60/minute")
def _parse_rate_limit(s: str) -> tuple[int, int]:
    m = re.match(r"(\d+)/(\d+)([smh])?", s.strip(), re.I)
    if not m:
        return 60, 60
    count, amount, unit = int(m[1]), int(m[2]), (m[3] or "s").lower()
    seconds = {"s": 1, "m": 60, "h": 3600}.get(unit, 1) * amount
    return count, seconds

RATE_LIMIT_COUNT, RATE_LIMIT_WINDOW = _parse_rate_limit(RATE_LIMIT_STR)
HSTS_MAX_AGE = int(os.getenv("PM_AGENT_HSTS_MAX_AGE", "31536000"))


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------
def _check_api_key(request: Request) -> bool:
    if not AUTH_ENABLED:
        return True
    if not AUTH_KEY:
        # Fail closed — no key configured means reject all to avoid accidental open access
        return False
    key = request.headers.get("x-api-key", "").strip()
    if key:
        return secrets.compare_digest(key, AUTH_KEY)
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return secrets.compare_digest(auth[7:].strip(), AUTH_KEY)
    return False


# ---------------------------------------------------------------------------
# Rate limiter — sliding window per IP
# ---------------------------------------------------------------------------
class SlidingWindowRateLimiter:
    """Thread-safe sliding-window rate limiter in-process."""

    def __init__(self, count: int, window: int) -> None:
        self.count = count
        self.window = window
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, key: str) -> tuple[bool, int, int]:
        """Returns (allowed, remaining, reset_in_seconds)."""
        now = time.monotonic()
        with self._lock:
            # Evict expired entries
            cutoff = now - self.window
            self._hits[key] = [t for t in self._hits[key] if t > cutoff]
            allowed = len(self._hits[key]) < self.count
            if allowed:
                self._hits[key].append(now)
            remaining = max(0, self.count - len(self._hits[key]))
            # Time until oldest entry expires
            reset_in = int(self.window - (now - (self._hits[key][0] if self._hits[key] else now)))
            return allowed, remaining, max(0, reset_in)


_rate_limiter = SlidingWindowRateLimiter(RATE_LIMIT_COUNT, RATE_LIMIT_WINDOW)


# ---------------------------------------------------------------------------
# Middleware stack
# ---------------------------------------------------------------------------
class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Public health/readiness endpoints
        if request.url.path in ("/", "/health", "/ready"):
            return await call_next(request)

        if not _check_api_key(request):
            return JSONResponse(
                status_code=401,
                content={
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32000, "message": "Unauthorized: valid X-API-Key required"},
                },
            )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # No rate limit on health endpoints
        if request.url.path in ("/", "/health", "/ready"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        allowed, remaining, reset_in = _rate_limiter.is_allowed(client_ip)

        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32001,
                        "message": f"Rate limit exceeded ({RATE_LIMIT_COUNT}/{RATE_LIMIT_WINDOW}s). Retry in {reset_in}s.",
                    },
                },
            )
            response.headers["Retry-After"] = str(reset_in)
            response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_COUNT)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(reset_in)
            return response

        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_COUNT)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["Strict-Transport-Security"] = (
            f"max-age={HSTS_MAX_AGE}; includeSubDomains; preload"
        )
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; "
            "form-action 'none'; frame-src 'none'; object-src 'none'"
        )
        # CORS — expose standard headers for SSE clients
        origin = request.headers.get("origin", "")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Headers"] = (
                "Content-Type, Accept, Authorization, X-API-Key, MCP-Session-Id"
            )
            response.headers["Access-Control-Expose-Headers"] = "MCP-Session-Id"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response.headers["Pragma"] = "no-cache"
        response.headers["Permissions-Policy"] = "accelerometer=(), camera=(), microphone=()"
        return response


# ---------------------------------------------------------------------------
# Build app
# ---------------------------------------------------------------------------
def build_app() -> None:
    app = mcp.http_app()
    # Order matters: rate limit → auth → security headers
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(ApiKeyAuthMiddleware)
    app.add_middleware(RateLimitMiddleware)
    return app


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "http"
    if mode == "http":
        app = build_app()
        config = Config(app=app, host="0.0.0.0", port=8212, log_level="info")
        server = Server(config)
        server.run()
    else:
        print(f"Unknown mode: {mode}", file=sys.stderr)
        sys.exit(1)