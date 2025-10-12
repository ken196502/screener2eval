"""
雪球行情数据服务
提供从雪球获取实时股票行情数据的功能
"""

import requests
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class XueqiuMarketData:
    """雪球行情数据服务类"""
    
    def __init__(self):
        self.session = requests.Session()
        self._setup_session()
    
    def _setup_session(self):
        """设置请求会话的cookies和headers"""
        # 雪球API所需的cookies
        cookies = {
            'cookiesu': '631739031524496',
            'device_id': '5981896b9cd1c172963c2b12f5f5c12f',
            's': 'bl16e3t3ba',
            'bid': '4b00aff9a838774878b7cd7b32843ae2_m810ojcu',
            'Hm_lvt_1db88642e346389874251b5a1eded6e3': '1758940715,1759634818,1760109127,1760244640',
            'HMACCOUNT': 'D3CD536C9DD13D6A',
            'remember': '1',
            'xq_a_token': '32cec461a3a0575e573092fdada6d9a0f8b0d0a5',
            'xqat': '32cec461a3a0575e573092fdada6d9a0f8b0d0a5',
            'xq_id_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJ1aWQiOjQzMDY0MTEzMjksImlzcyI6InVjIiwiZXhwIjoxNzYyNTYzNDU3LCJjdG0iOjE3NjAyNDQ2NzI4OTMsImNpZCI6ImQ5ZDBuNEFadXAifQ.L53hRU3vvtzbR2VIlX9ENIhW0TzPqensRuiIXTUc3A8Yf8l02lPc8N_iIomU5KuYOJ215vnFwuR11DWIrtMioKTT_6E9bTJ0vVK0OTPKeGT6_fyeJ19Muza2VgCMA1h_9T2Dhzld5eU75fUoSBCjbE9I72Em3EO5CUysWFXydbysVdL4mjdHFnE3EvUjTnnh0q1RI7cvMhh1kibEt-ZIMiKJ0-pqC2jwbSxGxzJmGR1DpAUlF3-cxiAO7H5DAulyoIFYxPoFdn_2zDFlXwwPSGRWO106CpJZk33l7i0AMB99tmZxcMoABxkCcxKSrqU_H5aVzGAhzfhmW-dN9qAuAQ',
            'xq_r_token': 'e22cb29d68e55974c31f4cb45b3e26f633aed15b',
            'xq_is_login': '1',
            'u': '4306411329',
            'is_overseas': '0',
            'Hm_lpvt_1db88642e346389874251b5a1eded6e3': '1760244687',
        }
        
        # 请求头
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6,ja;q=0.5',
            'origin': 'https://xueqiu.com',
            'priority': 'u=1, i',
            'referer': 'https://xueqiu.com/',
            'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        }
        
        # 设置会话的cookies和headers
        self.session.cookies.update(cookies)
        self.session.headers.update(headers)
    
    def get_kline_data(self, symbol: str, period: str = '1m', count: int = 100) -> Optional[Dict[str, Any]]:
        """
        获取K线数据
        
        Args:
            symbol: 股票代码，如 'MSFT'
            period: 时间周期，如 '1m', '5m', '15m', '30m', '1h', '1d'
            count: 获取数据条数，负数表示获取最新的数据
            
        Returns:
            包含K线数据的字典，失败返回None
        """
        try:
            # 当前时间戳（毫秒）
            current_timestamp = int(time.time() * 1000)
            
            # 构建请求URL
            url = 'https://stock.xueqiu.com/v5/stock/chart/kline.json'
            params = {
                'symbol': symbol,
                'begin': current_timestamp,
                'period': period,
                'type': 'before',
                'count': -abs(count),  # 使用负数获取最新数据
                'indicator': 'kline,pe,pb,ps,pcf,market_capital,agt,ggt,balance'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('error_code') == 0 or 'data' in data:
                return data
            else:
                logger.error(f"雪球API返回错误: {data}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"请求雪球API失败: {e}")
            return None
        except Exception as e:
            logger.error(f"解析雪球API数据失败: {e}")
            return None
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """
        获取最新价格
        
        Args:
            symbol: 股票代码
            
        Returns:
            最新价格，失败返回None
        """
        kline_data = self.get_kline_data(symbol, period='1m', count=1)
        
        if not kline_data or 'data' not in kline_data:
            return None
        
        data = kline_data['data']
        if not data.get('item') or len(data['item']) == 0:
            return None
        
        # 获取最新的一条数据
        latest_item = data['item'][0]
        
        # 根据column找到close价格的索引
        columns = data.get('column', [])
        if 'close' in columns:
            close_index = columns.index('close')
            if len(latest_item) > close_index:
                return float(latest_item[close_index])
        
        return None
    
    def parse_kline_data(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        解析K线数据为标准格式
        
        Args:
            raw_data: 从雪球API获取的原始数据
            
        Returns:
            解析后的K线数据列表
        """
        if not raw_data or 'data' not in raw_data:
            return []
        
        data = raw_data['data']
        columns = data.get('column', [])
        items = data.get('item', [])
        
        if not columns or not items:
            return []
        
        # 创建列名到索引的映射
        column_map = {col: i for i, col in enumerate(columns)}
        
        parsed_data = []
        
        for item in items:
            kline_dict = {}
            
            # 解析各个字段
            if 'timestamp' in column_map and len(item) > column_map['timestamp']:
                kline_dict['timestamp'] = item[column_map['timestamp']]
                kline_dict['datetime'] = datetime.fromtimestamp(item[column_map['timestamp']] / 1000)
            
            for field in ['open', 'high', 'low', 'close', 'volume', 'amount']:
                if field in column_map and len(item) > column_map[field]:
                    value = item[column_map[field]]
                    kline_dict[field] = float(value) if value is not None else None
            
            # 涨跌幅相关
            for field in ['chg', 'percent']:
                if field in column_map and len(item) > column_map[field]:
                    value = item[column_map[field]]
                    kline_dict[field] = float(value) if value is not None else None
            
            parsed_data.append(kline_dict)
        
        return parsed_data
    
    def get_market_status(self, symbol: str) -> Dict[str, Any]:
        """
        获取市场状态信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            市场状态信息
        """
        # 简单实现，基于时间判断市场状态
        # 实际项目中可以调用更详细的API
        current_time = datetime.now()
        hour = current_time.hour
        
        # 美股交易时间判断（简化版）
        if 21 <= hour <= 23 or 0 <= hour <= 4:  # 美股交易时间（北京时间）
            market_status = "TRADING"
        else:
            market_status = "CLOSED"
        
        return {
            "symbol": symbol,
            "market_status": market_status,
            "timestamp": int(time.time() * 1000),
            "current_time": current_time.isoformat()
        }


# 创建全局实例
xueqiu_client = XueqiuMarketData()


def get_last_price_from_xueqiu(symbol: str, market: str = "US") -> float:
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
    price = xueqiu_client.get_latest_price(symbol)
    if price is None or price <= 0:
        raise Exception(f"无法获取 {symbol} 的有效价格")
    return price


def get_kline_data_from_xueqiu(symbol: str, period: str = '1m', count: int = 100) -> List[Dict[str, Any]]:
    """
    从雪球获取K线数据
    
    Args:
        symbol: 股票代码
        period: 时间周期
        count: 数据条数
        
    Returns:
        K线数据列表
        
    Raises:
        Exception: 当无法获取K线数据时抛出异常
    """
    raw_data = xueqiu_client.get_kline_data(symbol, period, count)
    if not raw_data:
        raise Exception(f"无法获取 {symbol} 的K线数据")
    
    kline_data = xueqiu_client.parse_kline_data(raw_data)
    if not kline_data:
        raise Exception(f"解析 {symbol} 的K线数据失败")
    
    return kline_data