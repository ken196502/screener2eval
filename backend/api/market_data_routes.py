"""
市场数据API路由
提供股票行情数据的RESTful API接口
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

from services.market_data import get_last_price, get_kline_data, get_market_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/market", tags=["market_data"])


class PriceResponse(BaseModel):
    """价格响应模型"""
    symbol: str
    market: str
    price: float
    timestamp: int


class KlineItem(BaseModel):
    """K线数据项模型"""
    timestamp: int
    datetime: str
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: Optional[float]
    volume: Optional[float]
    amount: Optional[float]
    chg: Optional[float]
    percent: Optional[float]


class KlineResponse(BaseModel):
    """K线数据响应模型"""
    symbol: str
    market: str
    period: str
    count: int
    data: List[KlineItem]


class MarketStatusResponse(BaseModel):
    """市场状态响应模型"""
    symbol: str
    market: str = None
    market_status: str
    timestamp: int
    current_time: str


@router.get("/price/{symbol}", response_model=PriceResponse)
async def get_stock_price(symbol: str, market: str = "US"):
    """
    获取股票最新价格
    
    Args:
        symbol: 股票Symbol，如 'MSFT'
        market: 市场Symbol，默认 'US'
        
    Returns:
        包含最新价格的响应
    """
    try:
        price = get_last_price(symbol, market)
        
        import time
        return PriceResponse(
            symbol=symbol,
            market=market,
            price=price,
            timestamp=int(time.time() * 1000)
        )
    except Exception as e:
        logger.error(f"获取股票价格失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取股票价格失败: {str(e)}")


@router.get("/prices", response_model=List[PriceResponse])
async def get_multiple_prices(symbols: str, market: str = "US"):
    """
    批量获取多个股票的最新价格
    
    Args:
        symbols: 股票Symbol列表，逗号分隔，如 'MSFT,AAPL,TSLA'
        market: 市场Symbol，默认 'US'
        
    Returns:
        包含多个股票价格的响应列表
    """
    try:
        symbol_list = [s.strip() for s in symbols.split(',') if s.strip()]
        
        if not symbol_list:
            raise HTTPException(status_code=400, detail="股票Symbol列表不能为空")
        
        if len(symbol_list) > 20:
            raise HTTPException(status_code=400, detail="最多支持20个股票Symbol")
        
        results = []
        import time
        current_timestamp = int(time.time() * 1000)
        
        for symbol in symbol_list:
            try:
                price = get_last_price(symbol, market)
                results.append(PriceResponse(
                    symbol=symbol,
                    market=market,
                    price=price,
                    timestamp=current_timestamp
                ))
            except Exception as e:
                logger.warning(f"获取 {symbol} 价格失败: {e}")
                # 继续处理其他股票，不中断整个请求
                
        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量获取股票价格失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量获取股票价格失败: {str(e)}")


@router.get("/kline/{symbol}", response_model=KlineResponse)
async def get_stock_kline(
    symbol: str, 
    market: str = "US",
    period: str = "1m",
    count: int = 100
):
    """
    获取股票K线数据
    
    Args:
        symbol: 股票Symbol，如 'MSFT'
        market: 市场Symbol，默认 'US'
        period: 时间周期，支持 '1m', '5m', '15m', '30m', '1h', '1d'
        count: 数据条数，默认100，最大500
        
    Returns:
        包含K线数据的响应
    """
    try:
        # 参数验证 - yfinance支持的时间周期
        valid_periods = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max']
        if period not in valid_periods:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的时间周期，yfinance支持的周期: {', '.join(valid_periods)}"
            )
            
        if count <= 0 or count > 500:
            raise HTTPException(status_code=400, detail="数据条数必须在1-500之间")
        
        # 获取K线数据
        kline_data = get_kline_data(symbol, market, period, count)
        
        # 转换数据格式
        kline_items = []
        for item in kline_data:
            kline_items.append(KlineItem(
                timestamp=item.get('timestamp'),
                datetime=item.get('datetime').isoformat() if item.get('datetime') else None,
                open=item.get('open'),
                high=item.get('high'),
                low=item.get('low'),
                close=item.get('close'),
                volume=item.get('volume'),
                amount=item.get('amount'),
                chg=item.get('chg'),
                percent=item.get('percent')
            ))
        
        return KlineResponse(
            symbol=symbol,
            market=market,
            period=period,
            count=len(kline_items),
            data=kline_items
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取K线数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取K线数据失败: {str(e)}")


@router.get("/status/{symbol}", response_model=MarketStatusResponse)
async def get_stock_market_status(symbol: str, market: str = "US"):
    """
    获取股票市场状态
    
    Args:
        symbol: 股票Symbol，如 'MSFT'
        market: 市场Symbol，默认 'US'
        
    Returns:
        包含市场状态的响应
    """
    try:
        status_data = get_market_status(symbol, market)
        
        return MarketStatusResponse(
            symbol=status_data.get('symbol', symbol),
            market=status_data.get('market', market),
            market_status=status_data.get('market_status', 'UNKNOWN'),
            timestamp=status_data.get('timestamp'),
            current_time=status_data.get('current_time', '')
        )
    except Exception as e:
        logger.error(f"获取市场状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取市场状态失败: {str(e)}")


@router.get("/health")
async def market_data_health():
    """
    市场数据服务健康检查
    
    Returns:
        服务状态信息
    """
    try:
        # 测试获取一个价格来检查服务是否正常
        test_price = get_last_price("MSFT", "US")
        
        import time
        return {
            "status": "healthy",
            "timestamp": int(time.time() * 1000),
            "test_price": {
                "symbol": "MSFT.US",
                "price": test_price
            },
            "message": "市场数据服务运行正常"
        }
    except Exception as e:
        logger.error(f"市场数据服务健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "timestamp": int(time.time() * 1000),
            "error": str(e),
            "message": "市场数据服务异常"
        }