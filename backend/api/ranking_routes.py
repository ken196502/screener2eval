"""
Ranking API routes for factor-based stock rankings
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import pandas as pd
import requests
from datetime import datetime, timedelta

from database.connection import get_db
from database.models import StockKline
from factors import compute_all_factors, compute_selected_factors, list_factors, get_composite_score_columns

router = APIRouter(prefix="/api/ranking", tags=["ranking"])


@router.get("/factors")
async def get_available_factors():
    """Get list of available factors"""
    factors = list_factors()
    
    # Get all factor columns
    all_columns = []
    for factor in factors:
        all_columns.extend(factor.columns)
    
    # Add composite score columns
    all_columns.extend(get_composite_score_columns())
    
    return {
        "success": True,
        "factors": [
            {
                "id": factor.id,
                "name": factor.name,
                "description": factor.description,
                "columns": factor.columns
            }
            for factor in factors
        ],
        "all_columns": all_columns
    }


@router.get("/table")
async def get_ranking_table(
    db: Session = Depends(get_db),
    days: int = Query(100, description="Number of days of historical data to use"),
    factors: Optional[str] = Query(None, description="Comma-separated list of factor IDs to compute"),
    limit: int = Query(50, description="Maximum number of stocks to return")
):
    """Get ranking table based on factors computed from recent K-line data"""
    # Calculate date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Query K-line data for the specified period
    kline_query = db.query(StockKline).filter(
        StockKline.period == "1d",
        StockKline.datetime_str >= start_date.strftime("%Y-%m-%d"),
        StockKline.datetime_str <= end_date.strftime("%Y-%m-%d")
    ).order_by(StockKline.symbol, StockKline.timestamp)
    
    kline_data = kline_query.all()
    
    if not kline_data:
        return {
            "success": True,
            "data": [],
            "message": "No K-line data found for the specified period"
        }
    
    # Group data by symbol
    history = {}
    for kline in kline_data:
        symbol = kline.symbol
        if symbol not in history:
            history[symbol] = []
        
        history[symbol].append({
            "日期": kline.datetime_str,
            "开盘": float(kline.open_price) if kline.open_price else 0,
            "最高": float(kline.high_price) if kline.high_price else 0,
            "最低": float(kline.low_price) if kline.low_price else 0,
            "收盘": float(kline.close_price) if kline.close_price else 0,
            "成交量": float(kline.volume) if kline.volume else 0,
            "成交额": float(kline.amount) if kline.amount else 0,
        })
    
    # Convert to DataFrames
    history_dfs = {}
    for symbol, data in history.items():
        if len(data) >= 10:  # Minimum data requirement
            df = pd.DataFrame(data)
            df["日期"] = pd.to_datetime(df["日期"], format='mixed')
            history_dfs[symbol] = df.sort_values("日期")
    
    if not history_dfs:
        return {
            "success": True,
            "data": [],
            "message": "Insufficient data for factor calculation"
        }
    
    # Compute factors
    if factors:
        factor_ids = [f.strip() for f in factors.split(",")]
        result_df = compute_selected_factors(history_dfs, None, factor_ids)
    else:
        result_df = compute_all_factors(history_dfs, None)
    
    if result_df.empty:
        return {
            "success": True,
            "data": [],
            "message": "No factor results computed"
        }
    
    # Convert to list of dictionaries and limit results
    result_data = result_df.head(limit).to_dict('records')
    
    # Fill NaN values with None for JSON serialization
    for row in result_data:
        for key, value in row.items():
            if pd.isna(value):
                row[key] = None
    
    return {
        "success": True,
        "data": result_data,
        "total_symbols": len(history_dfs),
        "data_period": f"{start_date} to {end_date}",
        "factors_computed": factor_ids if factors else "all"
    }


@router.get("/symbols")
async def get_available_symbols(
    db: Session = Depends(get_db),
    days: int = Query(100, description="Number of days to check for data availability")
):
    """Get list of symbols with sufficient K-line data"""
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Query symbols with data in the specified period
    symbols_query = db.query(StockKline.symbol).filter(
        StockKline.period == "1d",
        StockKline.datetime_str >= start_date.strftime("%Y-%m-%d"),
        StockKline.datetime_str <= end_date.strftime("%Y-%m-%d")
    ).distinct()
    
    symbols = [row.symbol for row in symbols_query.all()]
    
    return {
        "success": True,
        "symbols": symbols,
        "count": len(symbols),
        "data_period": f"{start_date} to {end_date}"
    }


@router.get("/stock-info/{symbol}")
async def get_stock_basic_info(symbol: str):
    """Get basic information for a stock symbol from xueqiu"""
    try:
        # Read xueqiu token from cookies file
        try:
            from services.cookie_helper import get_xq_cookies
            cookies = get_xq_cookies()
            xq_token = None
            for cookie in cookies:
                if cookie.get('name') == 'xq_a_token':
                    xq_token = cookie.get('value')
                    break
        except:
            # Fallback to environment variable or default
            import os
            xq_token = os.getenv('XQ_TOKEN', '')
        
        if not xq_token:
            return {
                "success": False,
                "error": "XQ token not available",
                "data": []
            }
        
        # API call to xueqiu
        url = "https://stock.xueqiu.com/v5/stock/f10/us/company.json"
        params = {"symbol": symbol}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "cookie": f"xq_a_token={xq_token};"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "data": []
            }
        
        data_json = response.json()
        
        if "data" not in data_json:
            return {
                "success": False,
                "error": "No data in response",
                "data": []
            }
        
        # Convert to list of key-value pairs
        stock_info = []
        raw_data = data_json["data"]
        
        # Parse the company data
        if "company" in raw_data:
            company_data = raw_data["company"]
            
            # Handle both dict and string formats
            if isinstance(company_data, dict):
                company_dict = company_data
            elif isinstance(company_data, str):
                try:
                    company_dict = eval(company_data)
                except:
                    company_dict = {}
            else:
                company_dict = {}
            
            # 合并公司信息到公司简介
            profile_parts = []
            
            if "org_cn_introduction" in company_dict and company_dict["org_cn_introduction"]:
                profile_parts.append(company_dict["org_cn_introduction"])
                
            if "main_operation_business" in company_dict and company_dict["main_operation_business"]:
                profile_parts.append(f"【主营业务】{company_dict['main_operation_business']}")
                
            if "operating_scope" in company_dict and company_dict["operating_scope"]:
                profile_parts.append(f"【经营范围】{company_dict['operating_scope']}")
            
            if profile_parts:
                combined_profile = "\n\n".join(profile_parts)
                stock_info.append({"item": "公司简介", "value": combined_profile})
            if "staff_num" in company_dict and company_dict["staff_num"]:
                stock_info.append({"item": "员工人数", "value": f"{company_dict['staff_num']:,}"})
            if "org_website" in company_dict and company_dict["org_website"]:
                stock_info.append({"item": "官方网站", "value": company_dict["org_website"]})
        
        # Add any other fields from raw data
        for key, value in raw_data.items():
            if key != "company":  # Skip company as we handled it above
                stock_info.append({
                    "item": key,
                    "value": str(value) if value is not None else ""
                })
        
        return {
            "success": True,
            "data": stock_info,
            "symbol": symbol
        }
        
    except requests.RequestException as e:
        return {
            "success": False,
            "error": f"Request failed: {str(e)}",
            "data": []
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "data": []
        }