from typing import Dict, List, Any
import logging
from .xueqiu_market_data import get_last_price_from_xueqiu, get_kline_data_from_xueqiu

logger = logging.getLogger(__name__)

# 雪球股票代码映射（雪球使用的代码格式）
SYMBOL_MAPPING = {
    "AAPL.US": "AAPL",
    "TSLA.US": "TSLA", 
    "MSFT.US": "MSFT",
    "GOOGL.US": "GOOGL",
    "AMZN.US": "AMZN",
    "NVDA.US": "NVDA",
    "META.US": "META",
}


def get_last_price(symbol: str, market: str) -> float:
    """
    从雪球获取最新价格
    
    Args:
        symbol: 股票代码
        market: 市场代码
        
    Returns:
        最新价格
        
    Raises:
        Exception: 当无法获取价格时抛出异常
    """
    key = f"{symbol}.{market}"
    
    # 检查是否支持该股票
    if key not in SYMBOL_MAPPING:
        raise Exception(f"不支持的股票代码: {key}")
    
    xueqiu_symbol = SYMBOL_MAPPING[key]
    
    try:
        real_price = get_last_price_from_xueqiu(xueqiu_symbol, market)
        if real_price and real_price > 0:
            logger.info(f"从雪球获取 {key} 实时价格: {real_price}")
            return real_price
        else:
            raise Exception(f"雪球API返回无效价格: {real_price}")
    except Exception as e:
        logger.error(f"从雪球获取价格失败: {e}")
        raise Exception(f"无法获取 {key} 的实时价格: {str(e)}")


def get_kline_data(symbol: str, market: str, period: str = '1m', count: int = 100) -> List[Dict[str, Any]]:
    """
    从雪球获取K线数据
    
    Args:
        symbol: 股票代码
        market: 市场代码
        period: 时间周期
        count: 数据条数
        
    Returns:
        K线数据列表
        
    Raises:
        Exception: 当无法获取K线数据时抛出异常
    """
    key = f"{symbol}.{market}"
    
    # 检查是否支持该股票
    if key not in SYMBOL_MAPPING:
        raise Exception(f"不支持的股票代码: {key}")
    
    xueqiu_symbol = SYMBOL_MAPPING[key]
    
    try:
        kline_data = get_kline_data_from_xueqiu(xueqiu_symbol, period, count)
        if kline_data:
            logger.info(f"从雪球获取 {key} K线数据，共 {len(kline_data)} 条")
            return kline_data
        else:
            raise Exception(f"雪球API返回空的K线数据")
    except Exception as e:
        logger.error(f"从雪球获取K线数据失败: {e}")
        raise Exception(f"无法获取 {key} 的K线数据: {str(e)}")


def get_market_status(symbol: str, market: str) -> Dict[str, Any]:
    """
    从雪球获取市场状态
    
    Args:
        symbol: 股票代码
        market: 市场代码
        
    Returns:
        市场状态信息
        
    Raises:
        Exception: 当无法获取市场状态时抛出异常
    """
    from .xueqiu_market_data import xueqiu_client
    
    key = f"{symbol}.{market}"
    
    # 检查是否支持该股票
    if key not in SYMBOL_MAPPING:
        raise Exception(f"不支持的股票代码: {key}")
    
    xueqiu_symbol = SYMBOL_MAPPING[key]
    
    try:
        status_data = xueqiu_client.get_market_status(xueqiu_symbol)
        logger.info(f"从雪球获取 {key} 市场状态: {status_data.get('market_status')}")
        return status_data
    except Exception as e:
        logger.error(f"获取市场状态失败: {e}")
        raise Exception(f"无法获取 {key} 的市场状态: {str(e)}")
