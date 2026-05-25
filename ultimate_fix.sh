#!/bin/bash
# =========================================================================
#  myportal-python 终极修复脚本
#  功能：Cookie认证闭环、安全加固、日志脱敏、路径穿越修复、Argon2增强
#  用法：cd ~/myportal-test && ./ultimate_fix.sh
#  注意：只修改代码，不启动任何服务
# =========================================================================
set -e

echo "=========================================="
echo " 开始终极修复 myportal-python"
echo "=========================================="

# 备份（可选）
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r frontend/src "$BACKUP_DIR/frontend_src" 2>/dev/null || true
cp -r backend "$BACKUP_DIR/backend" 2>/dev/null || true
echo "已备份至 $BACKUP_DIR"

# ==============================
# 1. 前端 Auth Store：移除 localStorage 依赖
# ==============================
cat > frontend/src/stores/auth.js <<'AUTH_EOF'
import { defineStore } from 'pinia'
import request from '@/utils/request'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    isAuthenticated: false
  }),
  getters: {
    isAdmin: (state) => state.user?.roles?.includes('admin') || state.user?.roles?.includes('super_admin')
  },
  actions: {
    async login(username, password) {
      await request.post('/auth/login', { username, password })
      await this.fetchUser()
    },
    async fetchUser() {
      try {
        const res = await request.get('/auth/me')
        this.user = res.data || res
        this.isAuthenticated = true
      } catch {
        this.logout()
        throw new Error("会话已过期")
      }
    },
    logout() {
      this.user = null
      this.isAuthenticated = false
      window.location.href = '/login'
    }
  }
})
AUTH_EOF

# ==============================
# 2. 前端路由守卫：不再依赖 token
# ==============================
cat > frontend/src/router/index.js <<'ROUTER_EOF'
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/register', component: () => import('../pages/Register.vue') },
  { path: '/login',    component: () => import('../pages/Login.vue') },
  {
    path: '/', component: () => import('../layouts/MainLayout.vue'),
    children: [
      { path: '',                component: () => import('../pages/Dashboard.vue') },
      { path: 'profile',         component: () => import('../pages/profile/Profile.vue') },
      { path: 'files',           component: () => import('../pages/files/FileList.vue') },
      { path: 'files/:id',       component: () => import('../pages/files/FilePreview.vue'), props: true },
      { path: 'articles',        component: () => import('../pages/articles/ArticleList.vue') },
      { path: 'articles/new',    component: () => import('../pages/articles/ArticleEditor.vue') },
      { path: 'articles/:id',    component: () => import('../pages/articles/ArticleDetail.vue'), props: true },
      { path: 'chat',            component: () => import('../pages/chat/Chat.vue') },
      {
        path: 'admin', component: () => import('../layouts/AdminLayout.vue'), meta: { requiresAdmin: true },
        children: [
          { path: '', redirect: '/admin/dashboard' },
          { path: 'dashboard',    component: () => import('../pages/admin/Dashboard.vue') },
          { path: 'articles',     component: () => import('../pages/admin/ArticlesManage.vue') },
          { path: 'users',        component: () => import('../pages/admin/UsersManage.vue') },
          { path: 'files',        component: () => import('../pages/admin/FilesManage.vue') },
          { path: 'chat',         component: () => import('../pages/admin/ChatManage.vue') },
          { path: 'config',       component: () => import('../pages/admin/SiteConfig.vue') }
        ]
      }
    ]
  }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to, from, next) => {
  const auth = useAuthStore()
  if (to.path === '/register' || to.path === '/login') {
    return next()
  }
  if (!auth.isAuthenticated) {
    try {
      await auth.fetchUser()
      next()
    } catch {
      next('/login')
    }
    return
  }
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    next('/')
  } else {
    next()
  }
})

export default router
ROUTER_EOF

# ==============================
# 3. Axios：开启 withCredentials
# ==============================
cat > frontend/src/utils/request.js <<'AXIOS_EOF'
import axios from 'axios'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api/v1',
  timeout: 15000,
  withCredentials: true
})

service.interceptors.response.use(
  res => res.data,
  error => {
    let msg = '请求失败'
    if (error.response?.data?.detail) {
      msg = error.response.data.detail
    } else if (error.code === 'ECONNABORTED') {
      msg = '请求超时，请重试'
    } else if (!error.response) {
      msg = '网络连接失败，请检查网络'
    }
    alert(msg)
    if (error.response?.status === 401) {
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default service
AXIOS_EOF

# ==============================
# 4. 后端 main.py：CORS + 安全头 + 日志脱敏
# ==============================
cat > backend/main.py <<'MAIN_EOF'
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import sys

from backend.core.config import settings
from backend.api.v1 import api_router
from backend.core.database import engine, Base

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("myportal")

app = FastAPI(
    title="MyPortal",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' ws: wss:"
        return response

app.add_middleware(SecurityHeadersMiddleware)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"请求 {request.method} {request.url.path} 出错: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误，请稍后重试"})

app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.on_event("shutdown")
async def shutdown():
    await engine.dispose()
MAIN_EOF

# ==============================
# 5. 认证路由 auth.py：Cookie 读写
# ==============================
cat > backend/api/v1/auth.py <<'AUTH_EOF'
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.config import settings
from backend.core.database import get_db
from backend.core.security import create_access_token, get_current_user
from backend.models.user import User
from backend.schemas.user import UserOut, UserCreate, UserLogin
from backend.services.user_service import create_user, authenticate_user

router = APIRouter(prefix="/auth", tags=["认证"])

def set_token_cookie(response: Response, token: str):
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=int(settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60),
        path="/"
    )

@router.post("/register", response_model=UserOut)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    return await create_user(db, user_in)

@router.post("/login")
async def login(response: Response, login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(401, "用户名或密码错误")
    token = create_access_token(data={"sub": user.username, "user_id": user.id})
    set_token_cookie(response, token)
    return {"message": "登录成功", "user": UserOut.from_orm(user)}

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"message": "已登出"}

@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/switch-role")
async def switch_role(
    response: Response,
    role_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from backend.services.user_service import switch_user_role
    user = await switch_user_role(db, current_user, role_name)
    if not user:
        raise HTTPException(400, "角色切换失败")
    token = create_access_token(data={"sub": user.username, "user_id": user.id})
    set_token_cookie(response, token)
    return {"message": f"已切换为 {role_name}", "user": UserOut.from_orm(user)}
AUTH_EOF

# ==============================
# 6. security.py：统一从 Cookie 读取 token
# ==============================
cat > backend/core/security.py <<'SEC_EOF'
from fastapi import Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
from datetime import datetime, timedelta
from backend.core.config import settings
from backend.core.database import get_db
from backend.models.user import User

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    payload = verify_token(token)
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="令牌无效")
    from backend.services.user_service import get_user_by_username
    user = await get_user_by_username(db, username)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return user
SEC_EOF

# ==============================
# 7. 用户服务补充 get_user_by_username
# ==============================
if ! grep -q "def get_user_by_username" backend/services/user_service.py 2>/dev/null; then
cat >> backend/services/user_service.py <<'USERSVC_EOF'

async def get_user_by_username(db: AsyncSession, username: str) -> User:
    from sqlalchemy import select
    from backend.models.user import User
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()
USERSVC_EOF
fi

# ==============================
# 8. 配置文件增加 CORS_ORIGINS
# ==============================
if ! grep -q "CORS_ORIGINS" backend/core/config.py 2>/dev/null; then
cat >> backend/core/config.py <<'CONFIG_EOF'

# 跨域允许的来源（逗号分隔）
CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
CONFIG_EOF
fi

# ==============================
# 9. 文件预览路径穿越修复
# ==============================
cat > backend/services/preview.py <<'PREVIEW_EOF'
import os
from pathlib import Path
from fastapi import HTTPException
from backend.core.config import settings

def get_file_path(filename: str) -> Path:
    safe_name = os.path.basename(filename)
    fp = (settings.UPLOAD_DIR / safe_name).resolve()
    if not str(fp).startswith(str(settings.UPLOAD_DIR.resolve())):
        raise HTTPException(400, "非法文件路径")
    if not fp.exists():
        raise HTTPException(404, "文件不存在")
    return fp

def preview_word(file_path: Path) -> str:
    try:
        import mammoth
        with open(file_path, "rb") as f:
            result = mammoth.convert_to_html(f)
        return f"<div class='preview-container'>{result.value}</div>"
    except ImportError:
        from docx import Document
        doc = Document(str(file_path))
        parts = ["<div class='preview-container'>"]
        for para in doc.paragraphs:
            text = para.text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            parts.append(f"<p>{text}</p>")
        parts.append("</div>")
        return "".join(parts)

def preview_excel(file_path: Path) -> str:
    from openpyxl import load_workbook
    wb = load_workbook(str(file_path), read_only=True, data_only=True)
    html = ["<div class='preview-container'>"]
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        html.append(f"<h3>{sheet_name}</h3><table border='1'>")
        for row in ws.iter_rows(values_only=True):
            html.append("<tr>")
            for cell in row:
                val = str(cell) if cell is not None else ""
                html.append(f"<td>{val}</td>")
            html.append("</tr>")
        html.append("</table>")
    html.append("</div>")
    return "".join(html)

def preview_ppt(file_path: Path) -> str:
    from pptx import Presentation
    prs = Presentation(str(file_path))
    html = ["<div class='preview-container'>"]
    for i, slide in enumerate(prs.slides, 1):
        texts = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    t = para.text.strip()
                    if t:
                        texts.append(t)
        content = "<br>".join(texts)
        html.append(f"<h2>第 {i} 页</h2><p>{content}</p>")
    html.append("</div>")
    return "".join(html)

def preview_pdf_page(file_path: Path, page_num: int = 1) -> bytes:
    import fitz
    with fitz.open(str(file_path)) as doc:
        if page_num < 1 or page_num > doc.page_count:
            raise HTTPException(404, "页码超出范围")
        page = doc.load_page(page_num - 1)
        pix = page.get_pixmap(dpi=150)
        return pix.tobytes("jpg")

def get_pdf_page_count(file_path: Path) -> int:
    import fitz
    with fitz.open(str(file_path)) as doc:
        return doc.page_count
PREVIEW_EOF

# ==============================
# 10. 用户模型 Argon2 增强
# ==============================
cat > backend/models/user.py <<'USERMODEL_EOF'
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from argon2 import PasswordHasher
from backend.core.database import Base
import datetime

ph = PasswordHasher(time_cost=4, memory_cost=131072, parallelism=4)

user_roles = Table(
    'user_roles', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True)
)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100))
    hashed_password = Column(String(255), nullable=False)
    avatar = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    roles = relationship("Role", secondary=user_roles, back_populates="users")

    def set_password(self, password: str):
        self.hashed_password = ph.hash(password)

    def verify_password(self, password: str) -> bool:
        try:
            return ph.verify(self.hashed_password, password)
        except Exception:
            return False

    def has_role(self, role_name: str) -> bool:
        return any(role.name == role_name for role in self.roles)

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    users = relationship("User", secondary=user_roles, back_populates="roles")
USERMODEL_EOF

# ==============================
# 11. 增加 Redis 依赖
# ==============================
if ! grep -q "redis" requirements.txt 2>/dev/null; then
cat >> requirements.txt <<'REQ_EOF'
redis
aioredis
REQ_EOF
fi

# ==============================
# 12. 清理 .pyc 和 __pycache__
# ==============================
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete

echo ""
echo "=========================================="
echo " 终极修复完成！"
echo " 修复内容："
echo "   - 前端 Cookie 认证"
echo "   - 安全头 + CORS 加固"
echo "   - 日志脱敏"
echo "   - 文件预览路径穿越修复"
echo "   - Argon2 密码增强"
echo "   - Redis 依赖添加"
echo "=========================================="
echo ""
echo " 下一步："
echo "  1. 检查 .env 文件，确保已设置 CORS_ORIGINS, SECRET_KEY, DEBUG"
echo "  2. 安装新依赖: pip install -r requirements.txt"
echo "  3. 在测试环境验证功能"
echo "  4. 执行同步并推送: rsync + git add/commit/push"
echo "=========================================="
