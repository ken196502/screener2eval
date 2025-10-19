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
from factors import compute_all_factors, compute_selected_factors, list_factors

router = APIRouter(prefix="/api/ranking", tags=["ranking"])


@router.get("/factors")
async def get_available_factors():
    """Get list of available factors"""
    factors = list_factors()
    
    # Get all factor columns
    all_columns = []
    for factor in factors:
        all_columns.extend(factor.columns)
    
    # Add composite score column definition
    all_columns.append({
        "key": "综合评分",
        "label": "综合评分",
        "type": "score",
        "sortable": True
    })
    
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
    
    # Calculate composite score if multiple score columns exist
    score_columns = [col for col in result_df.columns if col.endswith('评分') or 'score' in col.lower()]
    if len(score_columns) > 0:
        # Calculate mean of all score columns, ignoring NaN
        result_df['综合评分'] = result_df[score_columns].mean(axis=1, skipna=True)
        # Sort by composite score descending
        result_df = result_df.sort_values('综合评分', ascending=False, na_position='last')
    
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
async def get_stock_basic_info(symbol: str, db: Session = Depends(get_db)):
    """Get basic information for a stock symbol using yfinance"""
    try:
        import yfinance as yf
        
        # Create ticker object
        ticker = yf.Ticker(symbol)
        
        # Get company info
        info = ticker.info
        
        if not info:
            return {
                "success": False,
                "error": "No data available for symbol",
                "data": []
            }
        
        # Convert to list of key-value pairs
        stock_info = []
        
        # Add company description/intro
        if "longBusinessSummary" in info and info["longBusinessSummary"]:
            stock_info.append({
                "item": "Business Summary", 
                "value": info["longBusinessSummary"]
            })
        
        # Add key company information
        key_fields = [
            ("Company Name", "longName"),
            ("Sector", "sector"),
            ("Industry", "industry"),
            ("Website", "website"),
            ("Country", "country"),
            ("Employees", "fullTimeEmployees"),
            ("Market Cap", "marketCap"),
            ("P/E Ratio", "trailingPE"),
            ("Forward P/E", "forwardPE"),
            ("PEG Ratio", "pegRatio"),
            ("Price to Book", "priceToBook"),
            ("Dividend Yield", "dividendYield"),
            ("Beta", "beta"),
            ("52 Week High", "fiftyTwoWeekHigh"),
            ("52 Week Low", "fiftyTwoWeekLow"),
            ("Volume", "volume"),
            ("Average Volume", "averageVolume"),
            ("Currency", "currency"),
            ("Exchange", "exchange"),
            ("Quote Type", "quoteType")
        ]
        
        for display_name, field_name in key_fields:
            if field_name in info and info[field_name] is not None:
                value = info[field_name]
                
                # Format numeric values
                if isinstance(value, (int, float)):
                    if field_name == "marketCap":
                        # Format market cap in billions/millions
                        if value >= 1e9:
                            value = f"${value/1e9:.2f}B"
                        elif value >= 1e6:
                            value = f"${value/1e6:.2f}M"
                        else:
                            value = f"${value:,.0f}"
                    elif field_name in ["trailingPE", "forwardPE", "pegRatio", "priceToBook", "beta", 
                                      "dividendYield", "fiftyTwoWeekHigh", "fiftyTwoWeekLow"]:
                        if field_name == "dividendYield":
                            value = f"{value*100:.2f}%"
                        else:
                            value = f"{value:.2f}"
                    elif field_name in ["volume", "averageVolume", "fullTimeEmployees"]:
                        value = f"{value:,}"
                
                stock_info.append({
                    "item": display_name,
                    "value": str(value)
                })
        
        return {
            "success": True,
            "data": stock_info,
            "symbol": symbol
        }
        
    except ImportError:
        return {
            "success": False,
            "error": "yfinance not available",
            "data": []
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error fetching data: {str(e)}",
            "data": []
        }