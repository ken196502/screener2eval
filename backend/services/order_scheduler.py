"""
订单调度服务
定期处理待成交订单的后台任务
"""

import asyncio
import threading
import time
import logging
from typing import Optional

from database.connection import SessionLocal
from .order_matching import process_all_pending_orders

logger = logging.getLogger(__name__)


class OrderScheduler:
    """订单调度器"""
    
    def __init__(self, interval_seconds: int = 5):
        """
        初始化订单调度器
        
        Args:
            interval_seconds: 检查间隔（秒）
        """
        self.interval_seconds = interval_seconds
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
    
    def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("订单调度器已经在运行")
            return
        
        self.running = True
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        logger.info(f"订单调度器已启动，检查间隔: {self.interval_seconds}秒")
    
    def stop(self):
        """停止调度器"""
        if not self.running:
            return
        
        self.running = False
        self._stop_event.set()
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=10)
        
        logger.info("订单调度器已停止")
    
    def _run_scheduler(self):
        """调度器主循环"""
        logger.info("订单调度器开始运行")
        
        while self.running and not self._stop_event.is_set():
            try:
                # 处理订单
                self._process_orders()
                
                # 等待下一次执行
                if self._stop_event.wait(timeout=self.interval_seconds):
                    break
                    
            except Exception as e:
                logger.error(f"订单调度器执行出错: {e}")
                # 出错后稍作等待，避免快速循环
                time.sleep(1)
        
        logger.info("订单调度器主循环结束")
    
    def _process_orders(self):
        """处理待成交订单"""
        db = SessionLocal()
        try:
            executed_count, total_checked = process_all_pending_orders(db)
            
            if total_checked > 0:
                logger.debug(f"订单处理: 检查 {total_checked} 个，成交 {executed_count} 个")
            
        except Exception as e:
            logger.error(f"处理订单时发生错误: {e}")
        finally:
            db.close()
    
    def process_orders_once(self):
        """手动执行一次订单处理"""
        if not self.running:
            logger.warning("订单调度器未运行，无法处理订单")
            return
        
        try:
            self._process_orders()
            logger.info("手动订单处理完成")
        except Exception as e:
            logger.error(f"手动处理订单失败: {e}")


# 全局调度器实例
order_scheduler = OrderScheduler(interval_seconds=5)


def start_order_scheduler():
    """启动全局订单调度器"""
    order_scheduler.start()


def stop_order_scheduler():
    """停止全局订单调度器"""
    order_scheduler.stop()


def get_scheduler_status():
    """获取调度器状态"""
    return {
        "running": order_scheduler.running,
        "interval_seconds": order_scheduler.interval_seconds,
        "thread_alive": order_scheduler.thread.is_alive() if order_scheduler.thread else False
    }