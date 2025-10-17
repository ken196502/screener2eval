from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict
import sys
import os

# 添加 services 路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services'))

from zhitong import (
    get_us_stock_movement_news,
    get_stock_news,
    parse_news_item,
    filter_us_stock_news,
    is_success_status,
    get_gmteight_news,
    parse_gmteight_news_item,
    filter_gmteight_stock_news,
)

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/us-stock-movement")
async def get_us_stock_movement(page: int = Query(1, ge=1, le=100)) -> Dict:
    """
    获取美股异动新闻
    
    参数:
        page: 页码，默认为1
    
    返回:
        美股异动新闻列表
    """
    try:
        news_list = get_us_stock_movement_news(page=page)
        return {
            "status": "success",
            "data": news_list,
            "page": page,
            "total": len(news_list)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取美股异动新闻失败: {str(e)}")


@router.get("/stock-news")
async def get_stock_news_api(
    page: int = Query(1, ge=1, le=100),
    news_type: str = Query("meigu", description="新闻类型，默认为美股")
) -> Dict:
    """
    获取股票新闻
    
    参数:
        page: 页码，默认为1
        news_type: 新闻类型，默认为'meigu'(美股)
    
    返回:
        股票新闻列表
    """
    try:
        result = get_stock_news(page=page, news_type=news_type)
        
        if not is_success_status(result.get('status')):
            raise HTTPException(status_code=400, detail=f"获取新闻失败，状态码: {result.get('status')}")
        
        news_data = result.get('data', {})
        news_list = news_data.get('list', [])
        
        # 解析新闻数据
        parsed_news = [parse_news_item(item) for item in news_list]
        
        return {
            "status": "success", 
            "data": parsed_news,
            "page": page,
            "total": len(parsed_news)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取股票新闻失败: {str(e)}")


@router.get("/us-stock-movement-filtered")
async def get_filtered_us_stock_movement(page: int = Query(1, ge=1, le=100)) -> Dict:
    """
    获取过滤后的美股异动新闻（仅包含"美股异动 |"开头的新闻）
    
    参数:
        page: 页码，默认为1
    
    返回:
        过滤后的美股异动新闻列表，包含股票代码
    """
    try:
        # 获取原始新闻
        result = get_stock_news(page=page, news_type="meigu")
        
        if not is_success_status(result.get('status')):
            raise HTTPException(status_code=400, detail=f"获取新闻失败，状态码: {result.get('status')}")
        
        news_data = result.get('data', {})
        news_list = news_data.get('list', [])
        
        # 解析新闻数据
        parsed_news = [parse_news_item(item) for item in news_list]
        
        # 过滤美股异动新闻并提取股票代码
        us_stock_news = filter_us_stock_news(parsed_news)
        
        return {
            "status": "success",
            "data": us_stock_news,
            "page": page,
            "total": len(us_stock_news),
            "filtered_from": len(parsed_news)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取过滤美股异动新闻失败: {str(e)}")


@router.get("/gmteight")
async def get_gmteight_news_api(
    page: int = Query(1, ge=1, le=100),
    page_size: int = Query(50, ge=1, le=200),
) -> Dict:
    """
    获取GMT Eight新闻

    参数:
        page: 页码，默认为1
        page_size: 每页数量，默认为50

    返回:
        GMT Eight新闻列表
    """
    try:
        result = get_gmteight_news(page=page, page_size=page_size)

        if not is_success_status(result.get('status')):
            raise HTTPException(status_code=400, detail=f"获取GMT Eight新闻失败，状态码: {result.get('status')}")

        news_data = result.get('data', {})
        news_list = news_data.get('list', [])
        parsed_news = [parse_gmteight_news_item(item) for item in news_list]
        filtered_news = filter_gmteight_stock_news(parsed_news)

        return {
            "status": "success",
            "data": filtered_news,
            "page": page,
            "total": len(filtered_news),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取GMT Eight新闻失败: {str(e)}")
