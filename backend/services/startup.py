"""
应用启动初始化服务
"""

import logging
from services.scheduler import start_scheduler, setup_market_tasks, task_scheduler

logger = logging.getLogger(__name__)


def initialize_services():
    """初始化所有服务"""
    try:
        # 初始化雪球cookie配置
        initialize_xueqiu_config()
        logger.info("雪球配置已初始化")
        
        # 启动调度器
        start_scheduler()
        logger.info("调度器服务已启动")
        
        # 设置市场相关定时任务
        setup_market_tasks()
        logger.info("市场定时任务已设置")
        
        logger.info("所有服务初始化完成")
        
    except Exception as e:
        logger.error(f"服务初始化失败: {e}")
        raise


def initialize_xueqiu_config():
    """从数据库初始化雪球cookie配置"""
    try:
        from database.connection import SessionLocal
        from database.models import SystemConfig
        from services.xueqiu_market_data import update_xueqiu_cookie
        
        db = SessionLocal()
        try:
            config = db.query(SystemConfig).filter(SystemConfig.key == "xueqiu_cookie").first()
            if config and config.value and config.value.strip():
                update_xueqiu_cookie(config.value)
                logger.info("雪球cookie配置已从数据库加载")
            else:
                logger.info("数据库中未找到雪球cookie配置")
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"初始化雪球配置失败: {e}")
        # 不抛出异常，让应用继续启动


def shutdown_services():
    """关闭所有服务"""
    try:
        from services.scheduler import stop_scheduler
        stop_scheduler()
        logger.info("所有服务已关闭")
        
    except Exception as e:
        logger.error(f"服务关闭失败: {e}")


# 可以在 FastAPI 应用的生命周期事件中调用
async def startup_event():
    """FastAPI 应用启动事件"""
    initialize_services()


async def shutdown_event():
    """FastAPI 应用关闭事件"""
    shutdown_services()