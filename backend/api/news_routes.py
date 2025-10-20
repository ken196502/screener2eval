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
        过滤后的美股异动新闻列表，包含股票Symbol
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
        
        # 过滤美股异动新闻并提取股票Symbol
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
    save_kline: bool = Query(False, description="是否保存股票K线数据"),
) -> Dict:
    """
    获取GMT Eight新闻，并可选择保存相关股票的K线数据

    参数:
        page: 页码，默认为1
        page_size: 每页数量，默认为50
        save_kline: 是否保存股票K线数据，默认为False

    返回:
        GMT Eight新闻列表，包含去重后的股票列表和K线保存状态
    """
    try:
        result = get_gmteight_news(page=page, page_size=page_size)

        if not is_success_status(result.get('status')):
            raise HTTPException(status_code=400, detail=f"获取GMT Eight新闻失败，状态码: {result.get('status')}")

        news_data = result.get('data', {})
        news_list = news_data.get('list', [])
        parsed_news = [parse_gmteight_news_item(item) for item in news_list]
        filtered_news = filter_gmteight_stock_news(parsed_news)

        # 提取并去重股票Symbol
        all_stock_codes = []
        for news in filtered_news:
            stock_codes = news.get('stock_codes', [])
            all_stock_codes.extend(stock_codes)
        
        # 去重股票列表，去掉.US后缀用于API调用
        unique_stocks = list(set([code.replace('.US', '') for code in all_stock_codes if code.endswith('.US')]))
        
        kline_save_status = {}
        
        # 如果需要保存K线数据
        if save_kline and unique_stocks:
            print(f"🔄 开始为 {len(unique_stocks)} 个去重股票获取和保存日K线数据...")
            
            # 确保雪球cookie已初始化
            from services.startup import initialize_xueqiu_config
            initialize_xueqiu_config()
            
            from services.market_data import get_kline_data
            from repositories.kline_repo import KlineRepository
            from database.connection import get_db
            
            db = next(get_db())
            kline_repo = KlineRepository(db)
            
            for i, symbol in enumerate(unique_stocks, 1):
                try:
                    print(f"📈 [{i}/{len(unique_stocks)}] 正在获取 {symbol} 的日K线数据...")
                    # 获取日K线数据，100条
                    kline_data = get_kline_data(symbol, "US", "1d", 100)
                    
                    # 添加短暂延迟避免请求过快  
                    import time
                    time.sleep(0.2)  # 增加延迟到200ms
                    
                    if kline_data:
                        print(f"✅ [{i}/{len(unique_stocks)}] {symbol} 获取到 {len(kline_data)} 条日K线数据，正在保存...")
                        # 保存到数据库（upsert模式）
                        save_result = kline_repo.save_kline_data(symbol, "US", "1d", kline_data)
                        inserted = save_result['inserted']
                        updated = save_result['updated']
                        total_processed = save_result['total']
                        
                        print(f"💾 [{i}/{len(unique_stocks)}] {symbol} 成功处理 {total_processed} 条数据 (新增:{inserted}, 更新:{updated})")
                        kline_save_status[symbol] = {
                            "status": "success",
                            "inserted_count": inserted,
                            "updated_count": updated,
                            "total_processed": total_processed,
                            "total_count": len(kline_data)
                        }
                    else:
                        kline_save_status[symbol] = {
                            "status": "no_data",
                            "message": "未获取到K线数据"
                        }
                        
                except Exception as e:
                    error_msg = str(e)
                    print(f"❌ [{i}/{len(unique_stocks)}] {symbol} 获取K线数据失败: {error_msg}")
                    
                    # 尝试重试一次
                    try:
                        print(f"🔄 [{i}/{len(unique_stocks)}] {symbol} 重试获取K线数据...")
                        time.sleep(1)  # 等待1秒后重试
                        kline_data = get_kline_data(symbol, "US", "1d", 100)
                        if kline_data:
                            print(f"✅ [{i}/{len(unique_stocks)}] {symbol} 重试成功，获取到 {len(kline_data)} 条数据")
                            save_result = kline_repo.save_kline_data(symbol, "US", "1d", kline_data)
                            inserted = save_result['inserted']
                            updated = save_result['updated']
                            total_processed = save_result['total']
                            print(f"💾 [{i}/{len(unique_stocks)}] {symbol} 重试处理 {total_processed} 条数据 (新增:{inserted}, 更新:{updated})")
                            kline_save_status[symbol] = {
                                "status": "success_retry",
                                "inserted_count": inserted,
                                "updated_count": updated,
                                "total_processed": total_processed,
                                "total_count": len(kline_data),
                                "note": "重试成功"
                            }
                        else:
                            kline_save_status[symbol] = {
                                "status": "error",
                                "message": f"重试仍失败: {error_msg}"
                            }
                    except Exception as e2:
                        kline_save_status[symbol] = {
                            "status": "error", 
                            "message": f"首次失败: {error_msg}, 重试失败: {str(e2)}"
                        }
            
            db.close()

        return {
            "status": "success",
            "data": filtered_news,
            "page": page,
            "total": len(filtered_news),
            "unique_stocks": unique_stocks,
            "unique_stocks_count": len(unique_stocks),
            "all_stock_codes": all_stock_codes,
            "kline_save_enabled": save_kline,
            "kline_save_status": kline_save_status if save_kline else {}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取GMT Eight新闻失败: {str(e)}")
