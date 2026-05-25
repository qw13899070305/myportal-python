from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.core.database import get_db
from backend.core.auth import RoleChecker
from backend.models.category import Category

router = APIRouter(prefix="/categories", tags=["分类"])

@router.get("/")
async def list_cat(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category))
    return result.scalars().all()

@router.post("/")
async def create_cat(name: str, db: AsyncSession = Depends(get_db),
                     _=Depends(RoleChecker(["admin","super_admin"]))):
    cat = Category(name=name)
    db.add(cat)
    await db.commit()
    return cat

@router.delete("/{cat_id}")
async def delete_cat(cat_id: int, db: AsyncSession = Depends(get_db),
                     _=Depends(RoleChecker(["admin","super_admin"]))):
    cat = await db.get(Category, cat_id)
    if not cat:
        raise HTTPException(404)
    await db.delete(cat)
    await db.commit()
    return {"ok": True}
