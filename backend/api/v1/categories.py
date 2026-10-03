"""文章分类接口。"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import RoleChecker
from backend.models.category import Category
from backend.models.user import User
from backend.schemas.article import CategoryCreate, CategoryOut
from backend.schemas.common import Message
from backend.services.audit import safe_log_action

router = APIRouter()

admin_only = RoleChecker(["admin", "super_admin"])


@router.get("/", response_model=list[CategoryOut])
async def list_cat(db: AsyncSession = Depends(get_db)):
    """全部分类（公开接口，无需登录）。"""
    result = await db.execute(select(Category).order_by(Category.name))
    return result.scalars().all()


@router.post("/", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_cat(
    request: Request,
    payload: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(admin_only),
):
    """新建分类（管理员）。"""
    exists = await db.scalar(select(Category).where(Category.name == payload.name))
    if exists is not None:
        raise HTTPException(status_code=400, detail="该分类已存在")

    category = Category(name=payload.name, description=payload.description)
    db.add(category)
    await db.commit()
    await safe_log_action(
        db,
        action="category_create",
        user_id=current_admin.id,
        detail=category.name,
        request=request,
    )
    return category


@router.delete("/{cat_id}", response_model=Message)
async def delete_cat(
    cat_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(admin_only),
):
    """删除分类（管理员）。"""
    category = await db.get(Category, cat_id)
    if category is None:
        raise HTTPException(status_code=404, detail="分类不存在")

    name = category.name
    await db.delete(category)
    await db.commit()
    await safe_log_action(
        db,
        action="category_delete",
        user_id=current_admin.id,
        detail=name,
        request=request,
    )
    return Message(message="分类已删除")
