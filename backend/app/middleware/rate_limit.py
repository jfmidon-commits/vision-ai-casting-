from fastapi import Request, HTTPException
from app.config import settings
import time

class RateLimiter:
    def __init__(self):
        self.requests = {}

    async def check(self, request: Request, limit: int, window: int = 60):
        client_ip = request.client.host
        key = f"{client_ip}:{request.url.path}"
        now = time.time()

        if key not in self.requests:
            self.requests[key] = []

        self.requests[key] = [t for t in self.requests[key] if now - t < window]

        if len(self.requests[key]) >= limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        self.requests[key].append(now)

rate_limiter = RateLimiter()
