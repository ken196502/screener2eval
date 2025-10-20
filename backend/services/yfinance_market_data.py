"""
yfinance市场数据服务
使用yfinance库获取美股实时行情数据
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


def get_last_price_from_yfinance(symbol: str, market: str = "US") -> float:
    """
    使用yfinance获取股票最新价格
    
    Args:
        symbol: 股票Symbol，如 'AAPL'
        market: 市场Symbol，默认为'US'
        
    Returns:
        最新价格
        
    Raises:
        Exception: 当无法获取价格时抛出异常
    """
    try:
        # yfinance可以直接处理美股Symbol，无需市场后缀
        ticker = yf.Ticker(symbol)
        
        # 获取实时数据
        info = ticker.info
        
        # 尝试获取不同的价格字段
        price_fields = ['regularMarketPrice', 'currentPrice', 'ask', 'bid', 'previousClose']
        
        for field in price_fields:
            price = info.get(field)
            if price and price > 0:
                logger.info(f"从yfinance获取 {symbol} 价格: {price} (字段: {field})")
                return float(price)
        
        # 如果实时价格字段都没有，尝试获取历史数据
        hist = ticker.history(period="1d", interval="1m")
        if not hist.empty:
            latest_price = hist['Close'].iloc[-1]
            logger.info(f"从yfinance历史数据获取 {symbol} 价格: {latest_price}")
            return float(latest_price)
        
        # 最后尝试获取昨天的收盘价
        previous_close = info.get('previousClose')
        if previous_close and previous_close > 0:
            logger.info(f"从yfinance获取 {symbol} 昨日收盘价: {previous_close}")
            return float(previous_close)
        
        raise Exception(f"无法获取 {symbol} 的有效价格")
        
    except Exception as e:
        logger.error(f"从yfinance获取 {symbol} 价格失败: {e}")
        raise Exception(f"yfinance API错误: {str(e)}")


def get_kline_data_from_yfinance(symbol: str, period: str = '1d', count: int = 100) -> List[Dict[str, Any]]:
    """
    使用yfinance获取K线数据
    
    Args:
        symbol: 股票Symbol
        period: 时间周期，支持 '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'
        count: 数据条数
        
    Returns:
        K线数据列表
    """
    try:
        # 映射API周期到yfinance支持的周期
        period_mapping = {
            '1d': '1d',
            '5d': '5d', 
            '1mo': '1mo',
            '3mo': '3mo',
            '6mo': '6mo',
            '1y': '1y',
            '2y': '2y',
            '5y': '5y',
            'ytd': 'ytd',
            'max': 'max'
        }
        
        # 处理分钟级数据
        interval_mapping = {
            '1m': '1m',
            '5m': '5m',
            '15m': '15m',
            '30m': '30m',
            '1h': '1h',
            '1d': '1d'
        }
        
        ticker = yf.Ticker(symbol)
        
        # 根据周期选择数据获取方式
        if period in ['1m', '5m', '15m', '30m', '1h']:
            # 分钟级数据，限制在7天内
            hist_period = '7d'
            hist_interval = interval_mapping[period]
            hist = ticker.history(period=hist_period, interval=hist_interval)
        elif period == '1d':
            # 日线数据，根据count计算需要的时间范围
            # 为了获取count条数据，需要考虑周末和节假日，获取更长的时间范围
            days_needed = int(count * 1.5)  # 预留50%的余量
            hist = ticker.history(period=f"{days_needed}d", interval='1d')
        else:
            # 其他周期数据（周线、月线等）
            hist_period = period_mapping.get(period, '1mo')
            hist = ticker.history(period=hist_period, interval='1d')
        
        if hist.empty:
            raise Exception(f"yfinance返回空的K线数据")
        
        # 限制数据条数
        hist = hist.tail(count)
        
        kline_data = []
        for idx, row in hist.iterrows():
            # 计算涨跌幅
            close = row['Close']
            open_price = row['Open']
            
            if open_price > 0:
                chg = close - open_price
                percent = (chg / open_price) * 100
            else:
                chg = 0
                percent = 0
            
            kline_item = {
                'timestamp': int(idx.timestamp() * 1000),  # 转换为毫秒
                'datetime': idx.strftime('%Y-%m-%d %H:%M:%S'),  # 转换为字符串
                'open': float(open_price),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(close),
                'volume': float(row['Volume']),
                'amount': 0,  # yfinance不提供成交额
                'chg': float(chg),
                'percent': float(percent)
            }
            kline_data.append(kline_item)
        
        logger.info(f"从yfinance获取 {symbol} K线数据，共 {len(kline_data)} 条")
        return kline_data
        
    except Exception as e:
        logger.error(f"从yfinance获取 {symbol} K线数据失败: {e}")
        raise Exception(f"yfinance K线数据获取错误: {str(e)}")


def get_market_status_from_yfinance(symbol: str) -> Dict[str, Any]:
    """
    使用yfinance获取市场状态
    
    Args:
        symbol: 股票Symbol
        
    Returns:
        市场状态信息
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # 判断市场状态
        exchange = info.get('exchange', '')
        market_status = 'OPEN'
        
        # 判断是否在交易时间
        current_time = datetime.now()
        
        # 简单的市场状态判断（实际应更精确）
        if exchange in ['NMS', 'NAS', 'NYQ']:  # 美股交易所
            # 美股交易时间: 9:30-16:00 ET
            # 这里简化处理，实际应该考虑时区和节假日
            market_status = 'OPEN'
        
        status_data = {
            'symbol': symbol,
            'market': 'US',
            'market_status': market_status,
            'timestamp': int(current_time.timestamp() * 1000),
            'current_time': current_time.isoformat()
        }
        
        logger.info(f"从yfinance获取 {symbol} 市场状态: {market_status}")
        return status_data
        
    except Exception as e:
        logger.error(f"从yfinance获取 {symbol} 市场状态失败: {e}")
        # 返回默认状态
        current_time = datetime.now()
        return {
            'symbol': symbol,
            'market': 'US',
            'market_status': 'UNKNOWN',
            'timestamp': int(current_time.timestamp() * 1000),
            'current_time': current_time.isoformat()
        }


class YFinanceClient:
    """yfinance客户端封装类"""
    
    def __init__(self):
        pass
    
    def get_last_price(self, symbol: str, market: str = "US") -> float:
        """获取最新价格"""
        return get_last_price_from_yfinance(symbol, market)
    
    def get_kline_data(self, symbol: str, period: str = '1d', count: int = 100) -> List[Dict[str, Any]]:
        """获取K线数据"""
        return get_kline_data_from_yfinance(symbol, period, count)
    
    def get_market_status(self, symbol: str) -> Dict[str, Any]:
        """获取市场状态"""
        return get_market_status_from_yfinance(symbol)


# 创建全局yfinance客户端实例
yfinance_client = YFinanceClient()