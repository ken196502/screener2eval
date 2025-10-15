"""
定时任务调度器服务
用于管理WebSocket快照更新和其他定时任务
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Set, Callable, Optional
import asyncio
import logging
from datetime import date

from database.connection import SessionLocal
from database.models import Position, StockPrice

logger = logging.getLogger(__name__)


class TaskScheduler:
    """统一的任务调度器"""
    
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self._started = False
        self._user_connections: Dict[int, Set] = {}  # 跟踪用户连接
        
    def start(self):
        """启动调度器"""
        if not self._started:
            self.scheduler = AsyncIOScheduler()
            self.scheduler.start()
            self._started = True
            logger.info("调度器已启动")
    
    def shutdown(self):
        """关闭调度器"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            self._started = False
            logger.info("调度器已关闭")
    
    def is_running(self) -> bool:
        """检查调度器是否运行中"""
        return self._started and self.scheduler and self.scheduler.running
    
    def add_user_snapshot_task(self, user_id: int, interval_seconds: int = 10):
        """
        为用户添加快照更新任务
        
        Args:
            user_id: 用户ID
            interval_seconds: 更新间隔（秒），默认10秒
        """
        if not self.is_running():
            self.start()
            
        job_id = f"snapshot_user_{user_id}"
        
        # 检查任务是否已存在
        if self.scheduler.get_job(job_id):
            logger.debug(f"用户 {user_id} 的快照任务已存在")
            return
        
        self.scheduler.add_job(
            func=self._execute_user_snapshot,
            trigger=IntervalTrigger(seconds=interval_seconds),
            args=[user_id],
            id=job_id,
            replace_existing=True,
            max_instances=1  # 避免重复执行
        )
        
        logger.info(f"已为用户 {user_id} 添加快照任务，间隔 {interval_seconds} 秒")
    
    def remove_user_snapshot_task(self, user_id: int):
        """
        移除用户的快照更新任务
        
        Args:
            user_id: 用户ID
        """
        if not self.scheduler:
            return
            
        job_id = f"snapshot_user_{user_id}"
        
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"已移除用户 {user_id} 的快照任务")
        except Exception as e:
            logger.debug(f"移除用户 {user_id} 快照任务失败: {e}")
    
    def add_market_hours_task(self, task_func: Callable, cron_expression: str, task_id: str):
        """
        添加基于市场时间的定时任务
        
        Args:
            task_func: 要执行的函数
            cron_expression: Cron表达式，例如 "0 9 * * 1-5" (工作日9点)
            task_id: 任务唯一标识
        """
        if not self.is_running():
            self.start()
            
        self.scheduler.add_job(
            func=task_func,
            trigger=CronTrigger.from_crontab(cron_expression),
            id=task_id,
            replace_existing=True
        )
        
        logger.info(f"已添加市场时间任务 {task_id}: {cron_expression}")
    
    def add_interval_task(self, task_func: Callable, interval_seconds: int, task_id: str, *args, **kwargs):
        """
        添加间隔执行任务
        
        Args:
            task_func: 要执行的函数
            interval_seconds: 执行间隔（秒）
            task_id: 任务唯一标识
            *args, **kwargs: 传递给task_func的参数
        """
        if not self.is_running():
            self.start()
            
        self.scheduler.add_job(
            func=task_func,
            trigger=IntervalTrigger(seconds=interval_seconds),
            args=args,
            kwargs=kwargs,
            id=task_id,
            replace_existing=True
        )
        
        logger.info(f"已添加间隔任务 {task_id}: 每 {interval_seconds} 秒执行")
    
    def remove_task(self, task_id: str):
        """
        移除指定任务
        
        Args:
            task_id: 任务ID
        """
        if not self.scheduler:
            return
            
        try:
            self.scheduler.remove_job(task_id)
            logger.info(f"已移除任务: {task_id}")
        except Exception as e:
            logger.debug(f"移除任务 {task_id} 失败: {e}")
    
    def get_job_info(self) -> list:
        """获取所有任务信息"""
        if not self.scheduler:
            return []
            
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'next_run_time': job.next_run_time,
                'func_name': job.func.__name__ if hasattr(job.func, '__name__') else str(job.func)
            })
        return jobs
    
    async def _execute_user_snapshot(self, user_id: int):
        """
        执行用户快照更新的内部方法
        
        Args:
            user_id: 用户ID
        """
        try:
            # 动态导入避免循环依赖
            from api.ws import manager, _send_snapshot
            
            # 检查用户是否还有活跃连接
            if user_id not in manager.active_connections:
                # 用户已断开连接，移除任务
                self.remove_user_snapshot_task(user_id)
                return
            
            # 执行快照更新
            db: Session = SessionLocal()
            try:
                # 发送快照更新
                await _send_snapshot(db, user_id)
                
                # 保存持仓股票的当日最新价格
                await self._save_position_prices(db, user_id)
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"用户 {user_id} 快照更新失败: {e}")
    
    async def _save_position_prices(self, db: Session, user_id: int):
        """
        保存用户持仓股票的当日最新价格
        
        Args:
            db: 数据库会话
            user_id: 用户ID
        """
        try:
            # 获取用户的所有持仓
            positions = db.query(Position).filter(
                Position.user_id == user_id,
                Position.quantity > 0
            ).all()
            
            if not positions:
                logger.debug(f"用户 {user_id} 没有持仓，跳过价格保存")
                return
            
            today = date.today()
            
            for position in positions:
                try:
                    # 检查今日是否已保存该股票价格
                    existing_price = db.query(StockPrice).filter(
                        StockPrice.symbol == position.symbol,
                        StockPrice.market == position.market,
                        StockPrice.price_date == today
                    ).first()
                    
                    if existing_price:
                        logger.debug(f"股票 {position.symbol} 今日价格已存在，跳过")
                        continue
                    
                    # 获取最新价格
                    from services.market_data import get_last_price
                    current_price = get_last_price(position.symbol, position.market)
                    
                    # 保存价格记录
                    stock_price = StockPrice(
                        symbol=position.symbol,
                        market=position.market,
                        price=current_price,
                        price_date=today
                    )
                    
                    db.add(stock_price)
                    db.commit()
                    
                    logger.info(f"已保存股票价格: {position.symbol} {today} {current_price}")
                    
                except Exception as e:
                    logger.error(f"保存股票 {position.symbol} 价格失败: {e}")
                    db.rollback()
                    continue
                    
        except Exception as e:
            logger.error(f"保存用户 {user_id} 持仓价格失败: {e}")
            db.rollback()


# 全局调度器实例
task_scheduler = TaskScheduler()


# 便捷函数
def start_scheduler():
    """启动全局调度器"""
    task_scheduler.start()


def stop_scheduler():
    """停止全局调度器"""
    task_scheduler.shutdown()


def add_user_snapshot_job(user_id: int, interval_seconds: int = 10):
    """为用户添加快照任务的便捷函数"""
    task_scheduler.add_user_snapshot_task(user_id, interval_seconds)


def remove_user_snapshot_job(user_id: int):
    """移除用户快照任务的便捷函数"""
    task_scheduler.remove_user_snapshot_task(user_id)


# 市场时间相关的预定义任务
async def market_open_tasks():
    """市场开盘时执行的任务"""
    logger.info("执行市场开盘任务")
    # 这里可以添加开盘时需要执行的逻辑
    # 例如：刷新市场数据、检查待处理订单等


async def market_close_tasks():
    """市场收盘时执行的任务"""
    logger.info("执行市场收盘任务")
    # 这里可以添加收盘时需要执行的逻辑
    # 例如：结算当日收益、生成报告等


def setup_market_tasks():
    """设置市场相关的定时任务"""
    # 美股开盘时间：周一到周五 9:30 AM ET (考虑时区转换)
    # 这里使用UTC时间，实际部署时需要根据服务器时区调整
    task_scheduler.add_market_hours_task(
        market_open_tasks,
        "30 14 * * 1-5",  # UTC时间，对应ET的9:30 AM
        "market_open"
    )
    
    # 美股收盘时间：周一到周五 4:00 PM ET
    task_scheduler.add_market_hours_task(
        market_close_tasks,
        "0 21 * * 1-5",   # UTC时间，对应ET的4:00 PM
        "market_close"
    )