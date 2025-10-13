from decimal import Decimal
from sqlalchemy.orm import Session
from database.models import Position
from .market_data import get_last_price


def calc_positions_value(db: Session, user_id: int) -> float:
    """
    计算持仓总市值
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        
    Returns:
        持仓总市值，如果无法获取价格则返回0
    """
    positions = db.query(Position).filter(Position.user_id == user_id).all()
    total = Decimal("0")
    
    for p in positions:
        try:
            price = Decimal(str(get_last_price(p.symbol, p.market)))
            total += price * Decimal(p.quantity)
        except Exception as e:
            # 记录错误但不中断计算，当无法获取价格时跳过该持仓
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"无法获取 {p.symbol}.{p.market} 价格，跳过该持仓价值计算: {e}")
            continue
    
    return float(total)
