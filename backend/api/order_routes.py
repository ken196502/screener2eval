"""
订单管理API路由
提供委托订单的创建、查询、取消等功能
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import logging

from database.connection import SessionLocal
from database.models import User, Order
from schemas.order import OrderCreate, OrderOut
from services.order_matching import create_order, check_and_execute_order, get_pending_orders, cancel_order, process_all_pending_orders
from repositories.user_repo import verify_user_password, user_has_password, set_user_password, verify_auth_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orders", tags=["orders"])


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class OrderCreateRequest(BaseModel):
    """创建订单请求模型"""
    user_id: int
    symbol: str
    name: str
    market: str = "US"
    side: str  # BUY/SELL
    order_type: str  # MARKET/LIMIT
    price: Optional[float] = None
    quantity: int
    username: Optional[str] = None  # Username for verification (required if no session_token)
    password: Optional[str] = None  # Trading password (required if no session_token)
    session_token: Optional[str] = None  # Auth session token (alternative to username+password)


class OrderExecutionResult(BaseModel):
    """订单执行结果模型"""
    order_id: int
    executed: bool
    message: str


class OrderProcessingResult(BaseModel):
    """订单处理结果模型"""
    executed_count: int
    total_checked: int
    message: str


@router.post("/create", response_model=OrderOut)
async def create_new_order(request: OrderCreateRequest, db: Session = Depends(get_db)):
    """
    创建委托订单
    
    Args:
        request: 订单创建请求
        db: 数据库会话
        
    Returns:
        创建的订单信息
    """
    try:
        # 获取用户
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 认证验证：支持session_token或用户名+密码两种方式
        if request.session_token:
            # 使用会话token认证（写死的180天免密功能）
            session_user_id = verify_auth_session(db, request.session_token)
            if session_user_id != request.user_id:
                raise HTTPException(status_code=401, detail="会话无效或已过期")
        elif request.username and request.password:
            # 使用用户名+密码认证
            if user.username != request.username:
                raise HTTPException(status_code=401, detail="用户名不匹配")
            
            # 密码验证
            if not user_has_password(db, request.user_id):
                # 首次交易，设置密码
                if len(request.password.strip()) < 4:
                    raise HTTPException(status_code=400, detail="密码长度至少4位")
                
                updated_user = set_user_password(db, request.user_id, request.password)
                if not updated_user:
                    raise HTTPException(status_code=500, detail="设置交易密码失败")
                
                logger.info(f"用户 {request.user_id} 首次交易，已设置交易密码")
            else:
                # 验证现有密码
                if not verify_user_password(db, request.user_id, request.password):
                    raise HTTPException(status_code=401, detail="交易密码错误")
        else:
            raise HTTPException(status_code=400, detail="请提供会话token或用户名+密码")
        
        # 创建订单
        order = create_order(
            db=db,
            user=user,
            symbol=request.symbol,
            name=request.name,
            market=request.market,
            side=request.side,
            order_type=request.order_type,
            price=request.price,
            quantity=request.quantity
        )
        
        db.commit()
        db.refresh(order)
        
        logger.info(f"用户 {user.username} 创建订单: {order.order_no}")
        return order
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"创建订单失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建订单失败: {str(e)}")


@router.get("/pending", response_model=List[OrderOut])
async def get_user_pending_orders(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    获取待成交订单
    
    Args:
        user_id: 用户ID，为空时获取所有用户的待成交订单
        db: 数据库会话
        
    Returns:
        待成交订单列表
    """
    try:
        orders = get_pending_orders(db, user_id)
        return orders
    except Exception as e:
        logger.error(f"获取待成交订单失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取待成交订单失败: {str(e)}")


@router.get("/user/{user_id}", response_model=List[OrderOut])
async def get_user_orders(user_id: int, status: Optional[str] = None, db: Session = Depends(get_db)):
    """
    获取用户的所有订单
    
    Args:
        user_id: 用户ID
        status: 订单状态过滤 (PENDING/FILLED/CANCELLED)
        db: 数据库会话
        
    Returns:
        用户订单列表
    """
    try:
        query = db.query(Order).filter(Order.user_id == user_id)
        
        if status:
            query = query.filter(Order.status == status)
        
        orders = query.order_by(Order.created_at.desc()).all()
        return orders
        
    except Exception as e:
        logger.error(f"获取用户订单失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取用户订单失败: {str(e)}")


@router.post("/execute/{order_id}", response_model=OrderExecutionResult)
async def execute_order_manually(order_id: int, db: Session = Depends(get_db)):
    """
    手动执行指定订单（检查成交条件）
    
    Args:
        order_id: 订单ID
        db: 数据库会话
        
    Returns:
        订单执行结果
    """
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        if order.status != "PENDING":
            return OrderExecutionResult(
                order_id=order_id,
                executed=False,
                message=f"订单状态为 {order.status}，无法执行"
            )
        
        # 检查并执行订单
        executed = check_and_execute_order(db, order)
        
        if executed:
            return OrderExecutionResult(
                order_id=order_id,
                executed=True,
                message="订单执行成功"
            )
        else:
            return OrderExecutionResult(
                order_id=order_id,
                executed=False,
                message="订单不满足成交条件"
            )
            
    except Exception as e:
        logger.error(f"执行订单失败: {e}")
        raise HTTPException(status_code=500, detail=f"执行订单失败: {str(e)}")


@router.post("/cancel/{order_id}")
async def cancel_user_order(order_id: int, reason: str = "用户取消", db: Session = Depends(get_db)):
    """
    取消订单
    
    Args:
        order_id: 订单ID
        reason: 取消原因
        db: 数据库会话
        
    Returns:
        取消结果
    """
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        if order.status != "PENDING":
            raise HTTPException(status_code=400, detail=f"订单状态为 {order.status}，无法取消")
        
        success = cancel_order(db, order, reason)
        
        if success:
            return {"message": "订单取消成功", "order_id": order_id}
        else:
            raise HTTPException(status_code=500, detail="订单取消失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消订单失败: {e}")
        raise HTTPException(status_code=500, detail=f"取消订单失败: {str(e)}")


@router.post("/process-all", response_model=OrderProcessingResult)
async def process_all_orders(db: Session = Depends(get_db)):
    """
    处理所有待成交订单
    
    Args:
        db: 数据库会话
        
    Returns:
        处理结果统计
    """
    try:
        executed_count, total_checked = process_all_pending_orders(db)
        
        return OrderProcessingResult(
            executed_count=executed_count,
            total_checked=total_checked,
            message=f"处理完成: 检查 {total_checked} 个订单，成交 {executed_count} 个"
        )
        
    except Exception as e:
        logger.error(f"处理订单失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理订单失败: {str(e)}")


@router.get("/order/{order_id}", response_model=OrderOut)
async def get_order_details(order_id: int, db: Session = Depends(get_db)):
    """
    获取订单详情
    
    Args:
        order_id: 订单ID
        db: 数据库会话
        
    Returns:
        订单详情
    """
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        return order
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取订单详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取订单详情失败: {str(e)}")


@router.get("/health")
async def orders_health_check(db: Session = Depends(get_db)):
    """
    订单服务健康检查
    
    Returns:
        服务状态信息
    """
    try:
        # 统计各状态订单数量
        total_orders = db.query(Order).count()
        pending_orders = db.query(Order).filter(Order.status == "PENDING").count()
        filled_orders = db.query(Order).filter(Order.status == "FILLED").count()
        cancelled_orders = db.query(Order).filter(Order.status == "CANCELLED").count()
        
        import time
        return {
            "status": "healthy",
            "timestamp": int(time.time() * 1000),
            "statistics": {
                "total_orders": total_orders,
                "pending_orders": pending_orders,
                "filled_orders": filled_orders,
                "cancelled_orders": cancelled_orders
            },
            "message": "订单服务运行正常"
        }
        
    except Exception as e:
        logger.error(f"订单服务健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "timestamp": int(time.time() * 1000),
            "error": str(e),
            "message": "订单服务异常"
        }