from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["健康检查"])

@router.get("/")
async def health_check():
    # 未来可增加数据库连接检查
    return {"status": "ok"}
