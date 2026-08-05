import math
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class InMemoryRateLimiter:
    """Small sliding-window limiter for the single-process local MVP."""

    def __init__(self) -> None:
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        now: float | None = None,
    ) -> None:
        current = time.monotonic() if now is None else now
        cutoff = current - window_seconds
        with self._lock:
            attempts = self._attempts[key]
            while attempts and attempts[0] <= cutoff:
                attempts.popleft()
            if len(attempts) >= limit:
                retry_after = max(1, math.ceil(window_seconds - (current - attempts[0])))
                raise HTTPException(
                    status_code=429,
                    detail="Bạn thao tác quá nhanh. Vui lòng thử lại sau.",
                    headers={"Retry-After": str(retry_after)},
                )
            attempts.append(current)

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)


rate_limiter = InMemoryRateLimiter()


def client_ip(request: Request) -> str:
    """Use the direct peer address; proxy headers require trusted-proxy setup."""
    return request.client.host if request.client else "unknown"


def chat_rate_key(request: Request) -> str:
    return f"chat:{client_ip(request)}"


def login_rate_key(request: Request, email: str) -> str:
    return f"login:{client_ip(request)}:{email.strip().lower()}"


def login_ip_rate_key(request: Request) -> str:
    return f"login-ip:{client_ip(request)}"
