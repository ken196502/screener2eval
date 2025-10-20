"""
K线数据仓库模块
提供K线数据的数据库操作功能
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from database.models import StockKline
from database.connection import get_db


class KlineRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_kline_data(self, symbol: str, market: str, period: str, kline_data: List[dict]) -> dict:
        """
        保存K线数据到数据库（使用upsert模式）
        
        Args:
            symbol: 股票Symbol
            market: 市场Symbol
            period: 时间周期
            kline_data: K线数据列表
            
        Returns:
            保存结果字典，包含新增和更新的数量
        """
        inserted_count = 0
        updated_count = 0
        
        for item in kline_data:
            timestamp = item.get('timestamp')
            if not timestamp:
                continue
                
            # 检查是否已存在相同时间戳的记录
            existing = self.db.query(StockKline).filter(
                and_(
                    StockKline.symbol == symbol,
                    StockKline.market == market,
                    StockKline.period == period,
                    StockKline.timestamp == timestamp
                )
            ).first()
            
            kline_data_dict = {
                'symbol': symbol,
                'market': market,
                'period': period,
                'timestamp': timestamp,
                'datetime_str': item.get('datetime', ''),
                'open_price': item.get('open'),
                'high_price': item.get('high'),
                'low_price': item.get('low'),
                'close_price': item.get('close'),
                'volume': item.get('volume'),
                'amount': item.get('amount'),
                'change': item.get('chg'),
                'percent': item.get('percent')
            }
            
            if existing:
                # 更新现有记录
                for key, value in kline_data_dict.items():
                    if key not in ['symbol', 'market', 'period', 'timestamp']:  # 不更新主键字段
                        setattr(existing, key, value)
                updated_count += 1
            else:
                # 插入新记录
                kline_record = StockKline(**kline_data_dict)
                self.db.add(kline_record)
                inserted_count += 1
        
        if inserted_count > 0 or updated_count > 0:
            self.db.commit()
            
        return {
            'inserted': inserted_count,
            'updated': updated_count,
            'total': inserted_count + updated_count
        }

    def get_kline_data(self, symbol: str, market: str, period: str, limit: int = 100) -> List[StockKline]:
        """
        获取K线数据
        
        Args:
            symbol: 股票Symbol
            market: 市场Symbol
            period: 时间周期
            limit: 限制数量
            
        Returns:
            K线数据列表
        """
        return self.db.query(StockKline).filter(
            and_(
                StockKline.symbol == symbol,
                StockKline.market == market,
                StockKline.period == period
            )
        ).order_by(StockKline.timestamp.desc()).limit(limit).all()

    def delete_old_kline_data(self, symbol: str, market: str, period: str, keep_days: int = 30):
        """
        删除旧的K线数据
        
        Args:
            symbol: 股票Symbol
            market: 市场Symbol
            period: 时间周期
            keep_days: 保留天数
        """
        import time
        cutoff_timestamp = int((time.time() - keep_days * 24 * 3600) * 1000)
        
        self.db.query(StockKline).filter(
            and_(
                StockKline.symbol == symbol,
                StockKline.market == market,
                StockKline.period == period,
                StockKline.timestamp < cutoff_timestamp
            )
        ).delete()
        
        self.db.commit()