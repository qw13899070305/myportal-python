import time
from collections import defaultdict
from fastapi import Request, HTTPException

class RateLimiter:
    def __init__(self, requests: int = 60, window: int = 60):
        self.requests = requests
        self.window = window
        self.clients = defaultdict(list)

    def __call__(self, request: Request):
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        self.clients[ip] = [t for t in self.clients[ip] if now - t < self.window]
        if len(self.clients[ip]) >= self.requests:
            raise HTTPException(429, "请求太频繁，请稍后再试")
        self.clients[ip].append(now)
