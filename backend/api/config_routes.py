"""
系统配置 API 路由
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging

from database.connection import SessionLocal
from database.models import SystemConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["config"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ConfigUpdateRequest(BaseModel):
    key: str
    value: str
    description: Optional[str] = None


@router.get("/xueqiu-cookie")
async def get_xueqiu_cookie_api(db: Session = Depends(get_db)):
    """获取雪球cookie配置"""
    try:
        # 首先尝试从数据库获取
        config = db.query(SystemConfig).filter(SystemConfig.key == "xueqiu_cookie").first()
        if config and config.value:
            # 如果数据库有配置，确保同步到全局变量
            from services.xueqiu_market_data import update_xueqiu_cookie
            update_xueqiu_cookie(config.value)
            return {
                "has_cookie": True,
                "value": config.value
            }
        else:
            # 如果数据库没有配置，检查全局变量
            from services.xueqiu_market_data import get_xueqiu_cookie
            cookie_value = get_xueqiu_cookie()
            return {
                "has_cookie": cookie_value is not None and cookie_value.strip() != "",
                "value": cookie_value
            }
    except Exception as e:
        logger.error(f"获取雪球cookie配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.post("/xueqiu-cookie")
async def update_xueqiu_cookie_api(request: ConfigUpdateRequest, db: Session = Depends(get_db)):
    """更新雪球cookie配置"""
    try:
        # 验证cookie长度
        if len(request.value) > 10000:
            raise HTTPException(status_code=400, detail="Cookie字符串太长，请确保长度不超过10000字符")
        
        # 保存到数据库
        config = db.query(SystemConfig).filter(SystemConfig.key == "xueqiu_cookie").first()
        if config:
            config.value = request.value
            if request.description:
                config.description = request.description
        else:
            config = SystemConfig(
                key="xueqiu_cookie",
                value=request.value,
                description=request.description or "雪球API访问Cookie"
            )
            db.add(config)
        
        db.commit()
        
        # 更新全局变量
        from services.xueqiu_market_data import update_xueqiu_cookie
        update_xueqiu_cookie(request.value)
        
        return {"success": True, "message": "雪球cookie配置已更新"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新雪球cookie配置失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@router.get("/check-required")
async def check_required_configs(db: Session = Depends(get_db)):
    """检查必需的配置是否已设置"""
    try:
        # 首先尝试从数据库获取
        config = db.query(SystemConfig).filter(SystemConfig.key == "xueqiu_cookie").first()
        if config and config.value and config.value.strip():
            # 如果数据库有配置，确保同步到全局变量
            from services.xueqiu_market_data import update_xueqiu_cookie
            update_xueqiu_cookie(config.value)
            has_xueqiu_cookie = True
        else:
            # 如果数据库没有配置，检查全局变量
            from services.xueqiu_market_data import get_xueqiu_cookie
            cookie_value = get_xueqiu_cookie()
            has_xueqiu_cookie = cookie_value is not None and cookie_value.strip() != ""
        
        return {
            "has_required_configs": has_xueqiu_cookie,
            "missing_configs": [] if has_xueqiu_cookie else ["xueqiu_cookie"]
        }
    except Exception as e:
        logger.error(f"检查必需配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"检查配置失败: {str(e)}")


@router.get("/cookie-help")
async def get_cookie_help():
    """获取Cookie配置帮助信息"""
    try:
        from services.cookie_helper import get_cookie_instructions, get_required_cookies, validate_cookie_string
        from services.xueqiu_market_data import get_xueqiu_cookie
        
        current_cookie = get_xueqiu_cookie()
        validation_result = None
        
        if current_cookie:
            validation_result = validate_cookie_string(current_cookie)
        
        return {
            "instructions": get_cookie_instructions(),
            "required_cookies": get_required_cookies(),
            "current_cookie_status": validation_result,
            "has_current_cookie": current_cookie is not None
        }
    except Exception as e:
        logger.error(f"获取Cookie帮助信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取帮助信息失败: {str(e)}")


@router.get("/test-xueqiu")
async def test_xueqiu_connection():
    """测试雪球连接和cookie有效性"""
    try:
        from services.xueqiu_market_data import get_xueqiu_cookie, xueqiu_client
        import requests
        
        # 检查cookie状态
        cookie = get_xueqiu_cookie()
        if not cookie:
            return {
                "success": False,
                "message": "Cookie未设置",
                "cookie_status": "not_set"
            }
        
        # 测试基本的API访问
        try:
            # 先测试股票信息API（更简单，无需begin参数）
            test_url = "https://stock.xueqiu.com/v5/stock/quote.json"
            params = {
                'symbol': 'AAPL',
                'extend': 'detail'
            }
            
            response = xueqiu_client.session.get(test_url, params=params, timeout=10)
            
            result = {
                "cookie_length": len(cookie),
                "api_status_code": response.status_code,
                "cookie_status": "unknown"
            }
            
            if response.status_code == 200:
                data = response.json()
                if data.get('error_code') == 0 or 'data' in data:
                    result.update({
                        "success": True,
                        "message": "雪球API访问正常",
                        "cookie_status": "valid",
                        "data_available": bool(data.get('data', {}).get('item') or data.get('data', {}).get('items'))
                    })
                else:
                    result.update({
                        "success": False,
                        "message": f"雪球API返回错误: {data}",
                        "cookie_status": "invalid"
                    })
            elif response.status_code == 400:
                try:
                    error_data = response.json()
                    result.update({
                        "success": False,
                        "message": f"雪球API 400错误: {error_data.get('error_description', '未知错误')}",
                        "cookie_status": "invalid",
                        "error_code": error_data.get('error_code')
                    })
                except:
                    result.update({
                        "success": False,
                        "message": f"雪球API 400错误，无法解析响应",
                        "cookie_status": "invalid"
                    })
            else:
                result.update({
                    "success": False,
                    "message": f"雪球API返回状态码: {response.status_code}",
                    "cookie_status": "invalid"
                })
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "message": f"雪球连接测试失败: {str(e)}",
                "cookie_status": "error",
                "cookie_length": len(cookie)
            }
            
    except Exception as e:
        logger.error(f"测试雪球连接失败: {e}")
        return {
            "success": False,
            "message": f"测试失败: {str(e)}",
            "cookie_status": "error"
        }