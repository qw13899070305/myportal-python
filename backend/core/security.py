import time, re
from collections import defaultdict
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import HTTPException, status
from backend.core.config import settings

ph = PasswordHasher()
login_attempts = defaultdict(lambda: {"count":0, "first_fail_time":0.0})

def hash_password(p: str) -> str: return ph.hash(p)
def verify_password(p: str, h: str) -> bool:
    try: return ph.verify(h, p)
    except VerifyMismatchError: return False

def check_login_throttle(ip: str):
    r = login_attempts[ip]
    if r["count"] >= settings.LOGIN_MAX_ATTEMPTS:
        elapsed = time.time() - r["first_fail_time"]
        if elapsed < settings.LOGIN_LOCKOUT_MINUTES * 60:
            raise HTTPException(429, f"登录锁定，{int((settings.LOGIN_LOCKOUT_MINUTES*60 - elapsed)/60)}分钟后再试")
        else:
            login_attempts[ip] = {"count":0, "first_fail_time":0.0}

def record_failed_login(ip: str):
    r = login_attempts[ip]
    if r["count"] == 0: r["first_fail_time"] = time.time()
    r["count"] += 1

def reset_login_attempts(ip: str):
    login_attempts[ip] = {"count":0, "first_fail_time":0.0}

def sanitize_html(text: str) -> str:
    if not text: return text
    return re.sub(r"<[^>]*>", "", text)

class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.CSP_POLICY:
            response.headers["Content-Security-Policy"] = settings.CSP_POLICY
        response.headers["Server"] = ""
        return response
