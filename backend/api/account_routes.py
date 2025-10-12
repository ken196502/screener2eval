"""
账户与持仓 API 路由
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional, List
import logging

from database.connection import SessionLocal
from database.models import User, Position
from repositories.user_repo import get_user
from repositories.position_repo import list_positions
from services.asset_calculator import calc_positions_value

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/account", tags=["account"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/overview")
async def get_overview(user_id: int, db: Session = Depends(get_db)):
    """获取账户资金概览"""
    try:
        user = get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        positions_value = calc_positions_value(db, user_id)
        return {
            "user": {
                "id": user.id,
                "username": user.username,
                "initial_capital": float(user.initial_capital),
                "current_cash": float(user.current_cash),
                "frozen_cash": float(user.frozen_cash),
            },
            "total_assets": positions_value + float(user.current_cash),
            "positions_value": positions_value,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取账户概览失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取账户概览失败: {str(e)}")


@router.get("/positions")
async def get_positions(user_id: int, db: Session = Depends(get_db)):
    """获取用户持仓列表"""
    try:
        user = get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        positions = list_positions(db, user_id)
        return [
            {
                "id": p.id,
                "user_id": p.user_id,
                "symbol": p.symbol,
                "name": p.name,
                "market": p.market,
                "quantity": p.quantity,
                "available_quantity": p.available_quantity,
                "avg_cost": float(p.avg_cost),
            }
            for p in positions
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取持仓失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取持仓失败: {str(e)}")
