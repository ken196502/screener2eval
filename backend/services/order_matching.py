"""
订单匹配服务
实现委托订单的条件成交逻辑
"""

import uuid
from decimal import Decimal
from typing import Optional, Tuple
from sqlalchemy.orm import Session
import logging

from database.models import Order, Position, Trade, User, US_MIN_COMMISSION, US_COMMISSION_RATE, US_MIN_ORDER_QUANTITY, US_LOT_SIZE
from .market_data import get_last_price

logger = logging.getLogger(__name__)


def _calc_commission(notional: Decimal) -> Decimal:
    """计算佣金"""
    pct_fee = notional * Decimal(str(US_COMMISSION_RATE))
    min_fee = Decimal(str(US_MIN_COMMISSION))
    return max(pct_fee, min_fee)


def create_order(db: Session, user: User, symbol: str, name: str, market: str, 
                side: str, order_type: str, price: Optional[float], quantity: int) -> Order:
    """
    创建委托订单
    
    Args:
        db: 数据库会话
        user: 用户对象
        symbol: 股票Symbol
        name: 股票名称
        market: 市场Symbol
        side: 买卖方向 (BUY/SELL)
        order_type: 订单类型 (MARKET/LIMIT)
        price: 委托价格 (限价单必填)
        quantity: 委托数量
        
    Returns:
        创建的订单对象
        
    Raises:
        ValueError: 参数验证失败或资金/持仓不足
    """
    # 基本参数验证
    if market != "US":
        raise ValueError("只支持美股市场")
    
    if quantity % US_LOT_SIZE != 0:
        raise ValueError(f"委托数量必须是 {US_LOT_SIZE} 的整数倍")
    
    if quantity < US_MIN_ORDER_QUANTITY:
        raise ValueError(f"委托数量必须 >= {US_MIN_ORDER_QUANTITY}")
    
    if order_type == "LIMIT" and (price is None or price <= 0):
        raise ValueError("限价单必须指定有效的委托价格")
    
    # 获取当前市价用于资金检查（仅在有cookie配置时）
    current_market_price = None
    if order_type == "MARKET":
        # 市价单获取当前价格进行资金校验
        try:
            current_market_price = get_last_price(symbol, market)
        except Exception as err:
            raise ValueError(f"市价单无法获取实时行情: {err}")
        check_price = Decimal(str(current_market_price))
    else:
        # 限价单使用委托价格进行资金检查
        check_price = Decimal(str(price))
    
    # 预先检查资金和持仓
    if side == "BUY":
        # 买入：检查现金是否足够
        notional = check_price * Decimal(quantity)
        commission = _calc_commission(notional)
        cash_needed = notional + commission
        
        if Decimal(str(user.current_cash)) < cash_needed:
            raise ValueError(f"现金不足。需要 ${cash_needed:.2f}，当前现金 ${user.current_cash:.2f}")
            
    else:  # SELL
        # 卖出：检查持仓是否足够
        position = (
            db.query(Position)
            .filter(Position.user_id == user.id, Position.symbol == symbol, Position.market == market)
            .first()
        )
        
        if not position or int(position.available_quantity) < quantity:
            available_qty = int(position.available_quantity) if position else 0
            raise ValueError(f"持仓不足。需要 {quantity} 股，可用持仓 {available_qty} 股")
    
    # 创建订单
    order = Order(
        version="v1",
        user_id=user.id,
        order_no=uuid.uuid4().hex[:16],
        symbol=symbol,
        name=name,
        market=market,
        side=side,
        order_type=order_type,
        price=price,
        quantity=quantity,
        filled_quantity=0,
        status="PENDING",
    )
    
    db.add(order)
    db.flush()
    
    logger.info(f"创建委托订单: {order.order_no}, {side} {quantity} {symbol} @ {price if price else 'MARKET'}")
    
    return order


def check_and_execute_order(db: Session, order: Order) -> bool:
    """
    检查并执行委托订单
    
    成交条件：
    - 买入：委托价格 >= 当前行情价格 且 资金足够
    - 卖出：委托价格 <= 当前行情价格 且 持仓足够
    
    Args:
        db: 数据库会话
        order: 待检查的订单
        
    Returns:
        是否成交
    """
    if order.status != "PENDING":
        return False
    
    # 检查是否有cookie配置，没有则跳过订单检查
    try:
        # 获取当前市价
        current_price = get_last_price(order.symbol, order.market)
        current_price_decimal = Decimal(str(current_price))
        
        # 获取用户信息
        user = db.query(User).filter(User.id == order.user_id).first()
        if not user:
            logger.error(f"订单 {order.order_no} 对应的用户不存在")
            return False
        
        # 检查成交条件
        should_execute = False
        execution_price = current_price_decimal
        
        if order.order_type == "MARKET":
            # 市价单立即成交
            should_execute = True
            execution_price = current_price_decimal
            
        elif order.order_type == "LIMIT":
            # 限价单条件成交
            limit_price = Decimal(str(order.price))
            
            if order.side == "BUY":
                # 买入：委托价格 >= 当前行情价格
                if limit_price >= current_price_decimal:
                    should_execute = True
                    execution_price = current_price_decimal  # 以市价成交
                    
            else:  # SELL
                # 卖出：委托价格 <= 当前行情价格
                if limit_price <= current_price_decimal:
                    should_execute = True
                    execution_price = current_price_decimal  # 以市价成交
        
        if not should_execute:
            logger.debug(f"订单 {order.order_no} 不满足成交条件: {order.side} {order.price} vs 市价 {current_price}")
            return False
        
        # 执行成交
        return _execute_order(db, order, user, execution_price)
        
    except Exception as e:
        logger.error(f"检查订单 {order.order_no} 时发生错误: {e}")
        return False


def _release_frozen_on_fill(user: User, order: Order, execution_price: Decimal, commission: Decimal):
    """在成交时释放冻结现金（仅BUY）"""
    if order.side == "BUY":
        # 估算被冻结的金额可能与实际成交不同，这里按实际成交金额释放
        notional = execution_price * Decimal(order.quantity)
        frozen_to_release = notional + commission
        user.frozen_cash = float(max(Decimal(str(user.frozen_cash)) - frozen_to_release, Decimal('0')))


def _execute_order(db: Session, order: Order, user: User, execution_price: Decimal) -> bool:
    """
    执行订单成交
    
    Args:
        db: 数据库会话
        order: 订单对象
        user: 用户对象
        execution_price: 成交价格
        
    Returns:
        是否成交成功
    """
    try:
        quantity = order.quantity
        notional = execution_price * Decimal(quantity)
        commission = _calc_commission(notional)
        
        # 再次检查资金和持仓（防止并发问题）
        if order.side == "BUY":
            cash_needed = notional + commission
            if Decimal(str(user.current_cash)) < cash_needed:
                logger.warning(f"订单 {order.order_no} 执行时现金不足")
                return False
                
            # 扣除现金
            user.current_cash = float(Decimal(str(user.current_cash)) - cash_needed)
            
            # 更新持仓
            position = (
                db.query(Position)
                .filter(Position.user_id == user.id, Position.symbol == order.symbol, Position.market == order.market)
                .first()
            )
            
            if not position:
                position = Position(
                    version="v1",
                    user_id=user.id,
                    symbol=order.symbol,
                    name=order.name,
                    market=order.market,
                    quantity=0,
                    available_quantity=0,
                    avg_cost=0,
                )
                db.add(position)
                db.flush()
            
            # 计算新的平均成本
            old_qty = int(position.quantity)
            old_cost = Decimal(str(position.avg_cost))
            new_qty = old_qty + quantity
            
            if old_qty == 0:
                new_avg_cost = execution_price
            else:
                new_avg_cost = (old_cost * Decimal(old_qty) + notional) / Decimal(new_qty)
            
            position.quantity = new_qty
            position.available_quantity = int(position.available_quantity) + quantity
            position.avg_cost = float(new_avg_cost)
            
        else:  # SELL
            # 检查持仓
            position = (
                db.query(Position)
                .filter(Position.user_id == user.id, Position.symbol == order.symbol, Position.market == order.market)
                .first()
            )
            
            if not position or int(position.available_quantity) < quantity:
                logger.warning(f"订单 {order.order_no} 执行时持仓不足")
                return False
            
            # 减少持仓
            position.quantity = int(position.quantity) - quantity
            position.available_quantity = int(position.available_quantity) - quantity
            
            # 增加现金
            cash_gain = notional - commission
            user.current_cash = float(Decimal(str(user.current_cash)) + cash_gain)
        
        # 创建成交记录
        trade = Trade(
            order_id=order.id,
            user_id=user.id,
            symbol=order.symbol,
            name=order.name,
            market=order.market,
            side=order.side,
            price=float(execution_price),
            quantity=quantity,
            commission=float(commission),
        )
        db.add(trade)

        # 释放冻结（BUY）
        _release_frozen_on_fill(user, order, execution_price, commission)
        
        # 更新订单状态
        order.filled_quantity = quantity
        order.status = "FILLED"
        
        db.commit()
        
        logger.info(f"订单 {order.order_no} 成交: {order.side} {quantity} {order.symbol} @ ${execution_price}")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"执行订单 {order.order_no} 时发生错误: {e}")
        return False


def get_pending_orders(db: Session, user_id: Optional[int] = None) -> list[Order]:
    """
    获取待成交订单
    
    Args:
        db: 数据库会话
        user_id: 用户ID，为None时获取所有用户的待成交订单
        
    Returns:
        待成交订单列表
    """
    query = db.query(Order).filter(Order.status == "PENDING")
    
    if user_id is not None:
        query = query.filter(Order.user_id == user_id)
    
    return query.order_by(Order.created_at).all()


def _release_frozen_on_cancel(user: User, order: Order):
    """取消订单时释放冻结（仅BUY）"""
    if order.side == "BUY":
        # 保守释放：按委托价格估算冻结金额，避免获取市价
        ref_price = float(order.price or 0.0)
        if ref_price <= 0:
            # 如果没有委托价格（理论上不应该发生），使用一个保守的估计
            logger.warning(f"订单 {order.order_no} 没有委托价格，无法准确释放冻结资金")
            ref_price = 100.0  # 使用一个默认值
        
        notional = Decimal(str(ref_price)) * Decimal(order.quantity)
        commission = _calc_commission(notional)
        release_amt = notional + commission
        user.frozen_cash = float(max(Decimal(str(user.frozen_cash)) - release_amt, Decimal('0')))


def cancel_order(db: Session, order: Order, reason: str = "用户取消") -> bool:
    """
    取消订单
    
    Args:
        db: 数据库会话
        order: 订单对象
        reason: 取消原因
        
    Returns:
        是否取消成功
    """
    if order.status != "PENDING":
        return False
    
    try:
        order.status = "CANCELLED"
        # 释放冻结
        user = db.query(User).filter(User.id == order.user_id).first()
        if user:
            _release_frozen_on_cancel(user, order)
        db.commit()
        
        logger.info(f"订单 {order.order_no} 已取消: {reason}")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"取消订单 {order.order_no} 时发生错误: {e}")
        return False


def process_all_pending_orders(db: Session) -> Tuple[int, int]:
    """
    处理所有待成交订单
    
    Args:
        db: 数据库会话
        
    Returns:
        (成交订单数, 总检查订单数)
    """
    pending_orders = get_pending_orders(db)
    executed_count = 0
    
    for order in pending_orders:
        if check_and_execute_order(db, order):
            executed_count += 1
    
    logger.info(f"处理待成交订单: 检查 {len(pending_orders)} 个，成交 {executed_count} 个")
    return executed_count, len(pending_orders)