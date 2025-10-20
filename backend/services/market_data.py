from typing import Dict, List, Any
import logging
from .yfinance_market_data import (
    get_last_price_from_yfinance,
    get_kline_data_from_yfinance,
    yfinance_client,
)
from .xueqiu_market_data import (
    get_last_price_from_xueqiu,
    get_kline_data_from_xueqiu,
    xueqiu_client,
    get_xueqiu_cookie,
)

logger = logging.getLogger(__name__)


def _check_xueqiu_cookie_available() -> bool:
    cookie = get_xueqiu_cookie()
    return bool(cookie and cookie.strip())


def get_last_price(symbol: str, market: str) -> float:
    key = f"{symbol}.{market}"
    logger.info(f"正在获取 {key} 的实时价格...")

    if _check_xueqiu_cookie_available():
        try:
            price = get_last_price_from_xueqiu(symbol, market)
            if price and price > 0:
                logger.info(f"从雪球获取 {key} 实时价格: {price}")
                return price
        except Exception as xq_err:
            logger.warning(f"雪球行情获取失败，尝试使用yfinance: {xq_err}")

    try:
        real_price = get_last_price_from_yfinance(symbol, market)
        if real_price and real_price > 0:
            logger.info(f"从yfinance获取 {key} 实时价格: {real_price}")
            return real_price
        raise Exception(f"yfinance返回无效价格: {real_price}")
    except Exception as yf_err:
        logger.error(f"从yfinance获取价格失败: {yf_err}")
        raise Exception(f"无法获取 {key} 的实时价格: {yf_err}")


def get_kline_data(symbol: str, market: str, period: str = "1d", count: int = 100) -> List[Dict[str, Any]]:
    key = f"{symbol}.{market}"

    if _check_xueqiu_cookie_available():
        try:
            data = get_kline_data_from_xueqiu(symbol, period, count)
            if data:
                logger.info(f"从雪球获取 {key} K线数据，共 {len(data)} 条")
                return data
        except Exception as xq_err:
            logger.warning(f"雪球K线获取失败，尝试使用yfinance: {xq_err}")

    try:
        kline_data = get_kline_data_from_yfinance(symbol, period, count)
        if kline_data:
            logger.info(f"从yfinance获取 {key} K线数据，共 {len(kline_data)} 条")
            return kline_data
        raise Exception("yfinance返回空的K线数据")
    except Exception as yf_err:
        logger.error(f"从yfinance获取K线数据失败: {yf_err}")
        raise Exception(f"无法获取 {key} 的K线数据: {yf_err}")


def get_market_status(symbol: str, market: str) -> Dict[str, Any]:
    key = f"{symbol}.{market}"

    if _check_xueqiu_cookie_available():
        try:
            status = xueqiu_client.get_market_status(symbol)
            logger.info(f"从雪球获取 {key} 市场状态: {status.get('market_status')}")
            return status
        except Exception as xq_err:
            logger.warning(f"雪球市场状态获取失败，尝试使用yfinance: {xq_err}")

    try:
        status_data = yfinance_client.get_market_status(symbol)
        logger.info(f"从yfinance获取 {key} 市场状态: {status_data.get('market_status')}")
        return status_data
    except Exception as yf_err:
        logger.error(f"获取市场状态失败: {yf_err}")
        raise Exception(f"无法获取 {key} 的市场状态: {yf_err}")
