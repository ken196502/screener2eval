"""
账户与持仓 API 路由
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
from decimal import Decimal
import logging

from database.connection import SessionLocal
from database.models import User, Position, Trade, StockPrice
from repositories.user_repo import (
    get_user, user_has_password, set_user_password, verify_user_password,
    create_auth_session, verify_auth_session, revoke_auth_session, revoke_all_user_sessions
)
from repositories.position_repo import list_positions
from services.asset_calculator import calc_positions_value
from schemas.user import PasswordSetRequest, PasswordVerifyRequest, AuthSessionResponse, AuthVerifyRequest, AuthLoginRequest

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
                "has_password": user_has_password(db, user_id),
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


@router.get("/asset-curve")
async def get_asset_curve(user_id: int, db: Session = Depends(get_db)):
    """获取用户资产曲线数据"""
    try:
        user = get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 获取第一笔成交时间
        first_trade = db.query(Trade).filter(Trade.user_id == user_id).order_by(Trade.trade_time.asc()).first()
        
        if not first_trade:
            # 如果没有成交记录，返回初始资金点
            return [{
                "date": datetime.now().date().isoformat(),
                "total_assets": float(user.initial_capital),
                "cash": float(user.current_cash),
                "positions_value": 0.0,
                "is_initial": True
            }]
        
        # 第一个点：第一笔成交前一天，值为初始资金
        first_trade_date = first_trade.trade_time.date()
        start_date = first_trade_date - timedelta(days=1)
        
        curve_data = []
        
        # 添加起始点
        curve_data.append({
            "date": start_date.isoformat(),
            "total_assets": float(user.initial_capital),
            "cash": float(user.initial_capital),
            "positions_value": 0.0,
            "is_initial": True
        })
        
        # 获取所有交易日期（有成交的日期）
        trade_dates = db.query(func.date(Trade.trade_time).label('trade_date')).filter(
            Trade.user_id == user_id
        ).distinct().order_by('trade_date').all()
        
        # 获取所有有价格数据的日期
        price_dates = db.query(StockPrice.price_date).distinct().order_by(StockPrice.price_date).all()
        
        # 合并并去重所有相关日期
        all_dates = set()
        for td in trade_dates:
            # 处理不同类型的日期对象
            if hasattr(td, 'trade_date'):
                trade_date = td.trade_date
            else:
                trade_date = td[0]  # 当使用label时，结果是元组
            
            if isinstance(trade_date, str):
                trade_date = datetime.strptime(trade_date, '%Y-%m-%d').date()
            elif hasattr(trade_date, 'date'):
                trade_date = trade_date.date()
            
            all_dates.add(trade_date)
            
        for pd in price_dates:
            # 处理价格日期
            if hasattr(pd, 'price_date'):
                price_date = pd.price_date
            else:
                price_date = pd[0]
                
            if isinstance(price_date, str):
                price_date = datetime.strptime(price_date, '%Y-%m-%d').date()
            elif hasattr(price_date, 'date'):
                price_date = price_date.date()
                
            all_dates.add(price_date)
        
        # 过滤出第一笔成交日期之后的日期
        relevant_dates = sorted([d for d in all_dates if d >= first_trade_date])
        
        for target_date in relevant_dates:
            try:
                # 计算到该日期为止的现金变化
                cash_changes = _calculate_cash_changes_up_to_date(db, user_id, target_date)
                current_cash = float(user.initial_capital) + cash_changes
                
                # 计算该日期的持仓价值
                positions_value = _calculate_positions_value_on_date(db, user_id, target_date)
                
                total_assets = current_cash + positions_value
                
                curve_data.append({
                    "date": target_date.isoformat(),
                    "total_assets": total_assets,
                    "cash": current_cash,
                    "positions_value": positions_value,
                    "is_initial": False
                })
                
            except Exception as e:
                logger.warning(f"计算日期 {target_date} 的资产失败: {e}")
                continue
        
        return curve_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取资产曲线失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取资产曲线失败: {str(e)}")


def _calculate_cash_changes_up_to_date(db: Session, user_id: int, target_date: date) -> float:
    """计算到指定日期为止的现金变化（买入为负，卖出为正）"""
    trades = db.query(Trade).filter(
        Trade.user_id == user_id,
        func.date(Trade.trade_time) <= target_date
    ).all()
    
    cash_change = 0.0
    for trade in trades:
        trade_amount = float(trade.price) * trade.quantity + float(trade.commission)
        if trade.side == "BUY":
            cash_change -= trade_amount  # 买入减少现金
        else:  # SELL
            cash_change += trade_amount  # 卖出增加现金
    
    return cash_change


def _calculate_positions_value_on_date(db: Session, user_id: int, target_date: date) -> float:
    """计算指定日期的持仓价值"""
    # 获取到该日期为止的所有交易，计算每个股票的持仓数量
    trades = db.query(Trade).filter(
        Trade.user_id == user_id,
        func.date(Trade.trade_time) <= target_date
    ).order_by(Trade.trade_time.asc()).all()
    
    # 统计每个股票的净持仓
    position_quantities = {}
    for trade in trades:
        key = f"{trade.symbol}.{trade.market}"
        if key not in position_quantities:
            position_quantities[key] = {"symbol": trade.symbol, "market": trade.market, "quantity": 0}
        
        if trade.side == "BUY":
            position_quantities[key]["quantity"] += trade.quantity
        else:  # SELL
            position_quantities[key]["quantity"] -= trade.quantity
    
    # 计算持仓价值
    total_value = 0.0
    for pos_info in position_quantities.values():
        if pos_info["quantity"] <= 0:
            continue
            
        # 获取该日期的股票价格
        stock_price = db.query(StockPrice).filter(
            StockPrice.symbol == pos_info["symbol"],
            StockPrice.market == pos_info["market"],
            StockPrice.price_date <= target_date
        ).order_by(StockPrice.price_date.desc()).first()
        
        if stock_price:
            position_value = float(stock_price.price) * pos_info["quantity"]
            total_value += position_value
        else:
            logger.warning(f"未找到 {pos_info['symbol']} 在 {target_date} 的价格数据")
    
    return total_value


@router.post("/password/set")
async def set_password(user_id: int, request: PasswordSetRequest, db: Session = Depends(get_db)):
    """设置或更新交易密码"""
    try:
        user = get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        if not request.password or len(request.password.strip()) < 4:
            raise HTTPException(status_code=400, detail="密码长度至少4位")
        
        updated_user = set_user_password(db, user_id, request.password)
        if not updated_user:
            raise HTTPException(status_code=500, detail="密码设置失败")
        
        return {"message": "交易密码设置成功"}
    
    except Exception as e:
        logger.error(f"设置交易密码失败: {e}")
        raise HTTPException(status_code=500, detail="设置交易密码失败")


@router.post("/password/verify")
async def verify_password(user_id: int, request: PasswordVerifyRequest, db: Session = Depends(get_db)):
    """验证交易密码"""
    try:
        user = get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        if not user_has_password(db, user_id):
            raise HTTPException(status_code=400, detail="用户尚未设置交易密码")
        
        is_valid = verify_user_password(db, user_id, request.password)
        
        return {"valid": is_valid}
    
    except Exception as e:
        logger.error(f"验证交易密码失败: {e}")
        raise HTTPException(status_code=500, detail="验证交易密码失败")


@router.post("/auth/login", response_model=AuthSessionResponse)
async def create_auth_session_endpoint(user_id: int, request: AuthLoginRequest, db: Session = Depends(get_db)):
    """创建认证会话（180天有效期）- 写死功能"""
    try:
        user = get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 验证用户名是否匹配
        if user.username != request.username:
            raise HTTPException(status_code=401, detail="用户名不匹配")
        
        # 密码验证 - 支持首次设置
        if not user_has_password(db, user_id):
            # 首次交易，设置密码
            if len(request.password.strip()) < 4:
                raise HTTPException(status_code=400, detail="密码长度至少4位")
            
            updated_user = set_user_password(db, user_id, request.password)
            if not updated_user:
                raise HTTPException(status_code=500, detail="设置交易密码失败")
            
            logger.info(f"用户 {user_id} 首次认证，已设置交易密码")
        else:
            # 验证现有密码
            if not verify_user_password(db, user_id, request.password):
                raise HTTPException(status_code=401, detail="交易密码错误")
        
        # 创建会话
        session = create_auth_session(db, user_id)
        if not session:
            raise HTTPException(status_code=500, detail="创建认证会话失败")
        
        return AuthSessionResponse(
            session_token=session.session_token,
            expires_at=session.expires_at.isoformat(),
            message="认证会话创建成功，180天内有效"
        )
    
    except Exception as e:
        logger.error(f"创建认证会话失败: {e}")
        raise HTTPException(status_code=500, detail="创建认证会话失败")


@router.post("/auth/verify")
async def verify_auth_session_endpoint(request: AuthVerifyRequest, db: Session = Depends(get_db)):
    """验证认证会话是否有效"""
    try:
        user_id = verify_auth_session(db, request.session_token)
        
        if user_id is None:
            return {"valid": False, "message": "会话无效或已过期"}
        
        return {"valid": True, "user_id": user_id, "message": "会话有效"}
    
    except Exception as e:
        logger.error(f"验证认证会话失败: {e}")
        raise HTTPException(status_code=500, detail="验证认证会话失败")


@router.post("/auth/logout")
async def logout_auth_session(request: AuthVerifyRequest, db: Session = Depends(get_db)):
    """注销认证会话"""
    try:
        success = revoke_auth_session(db, request.session_token)
        
        if success:
            return {"message": "会话已注销"}
        else:
            return {"message": "会话不存在或已过期"}
    
    except Exception as e:
        logger.error(f"注销认证会话失败: {e}")
        raise HTTPException(status_code=500, detail="注销认证会话失败")


@router.post("/auth/logout-all")
async def logout_all_sessions(user_id: int, db: Session = Depends(get_db)):
    """注销用户所有认证会话"""
    try:
        user = get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        deleted_count = revoke_all_user_sessions(db, user_id)
        
        return {"message": f"已注销 {deleted_count} 个会话"}
    
    except Exception as e:
        logger.error(f"注销所有会话失败: {e}")
        raise HTTPException(status_code=500, detail="注销所有会话失败")
