import time
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

login_attempts = defaultdict(list)
MAX_ATTEMPTS = 5
BLOCK_TIME = 300

class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/api/v1/auth/login" and request.method == "POST":
            ip = request.client.host
            now = time.time()
            login_attempts[ip] = [t for t in login_attempts[ip] if now - t < BLOCK_TIME]
            if len(login_attempts[ip]) >= MAX_ATTEMPTS:
                raise HTTPException(429, detail="登录过于频繁，请5分钟后再试")
        response = await call_next(request)
        if response.status_code == 401 and request.url.path == "/api/v1/auth/login":
            login_attempts[request.client.host].append(time.time())
        return response
