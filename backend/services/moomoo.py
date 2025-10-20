import requests
import json
import time
from typing import Optional, Dict, Any


def get_topics_news(
    topics_id: int = 447,
    page: int = 1,
    page_size: int = 48,
    is_translate: int = 1,
    proxy: str = "http://127.0.0.1:7890"
) -> Optional[Dict[str, Any]]:
    """
    获取主题新闻列表
    
    Args:
        topics_id: 主题ID，默认447（美股市场动态）
        page: 页码，默认3
        page_size: 每页数量，默认48
        is_translate: 是否翻译，默认1
        proxy: 代理地址，默认 http://127.0.0.1:7890
        
    Returns:
        返回API响应的JSON数据，失败返回None
    """
    base_url = "https://www.moomoo.com/news/news-site-api/topic/get-topics-news-list"
    
    params = {
        'topicsId': topics_id,
        'page': page,
        'pageSize': page_size,
        'isTranslate': is_translate,
        '_t': int(time.time() * 1000)
    }
    
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6,ja;q=0.5',
        'priority': 'u=1, i',
        'referer': 'https://www.moomoo.com/news/news-topics/447/us-market-movers',
        'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        'x-news-nuxt-country-code': 'KR',
        'x-news-site-lang': '2'
    }
    
    cookies = {
        'locale': 'en-us',
        'FUTU_TIMEZONE': 'Asia/Shanghai'
    }
    
    proxies = {
        "http": proxy,
        "https": proxy
    } if proxy else None
    
    try:
        response = requests.get(
            base_url,
            params=params,
            headers=headers,
            cookies=cookies,
            proxies=proxies,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None


def get_stock_data(topics_id: int = 447, page: int = 3, proxy: str = "http://127.0.0.1:7890") -> Optional[list]:
    """
    获取股票数据列表
    
    Args:
        topics_id: 主题ID
        page: 页码
        proxy: 代理地址
        
    Returns:
        返回股票数据列表，失败返回None
    """
    result = get_topics_news(topics_id=topics_id, page=page, proxy=proxy)
    
    if result and result.get('code') == 0:
        return result.get('data', {}).get('data', [])
    return None


def print_stock_info(topics_id: int = 447, page: int = 3, proxy: str = "http://127.0.0.1:7890"):
    """
    打印股票信息
    
    Args:
        topics_id: 主题ID
        page: 页码
        proxy: 代理地址
    """
    data = get_stock_data(topics_id=topics_id, page=page, proxy=proxy)
    
    if not data:
        print("未获取到数据")
        return
    
    print(f"\n共获取到 {len(data)} 条数据\n")
    
    for item in data:
        if 'quote' in item and item['quote']:
            quote = item['quote'][0]
            print(f"股票Symbol: {quote.get('code', 'N/A')}")
            print(f"股票名称: {quote.get('name', 'N/A')}")
            print(f"当前价格: {quote.get('price', 'N/A')}")
            print(f"涨跌幅: {quote.get('changeRatio', 'N/A')}")
            print(f"涨跌额: {quote.get('changePrice', 'N/A')}")
            print(f"链接: {quote.get('quoteUrl', 'N/A')}")
            print("-" * 60)


def main():
    """主函数示例"""
    proxy = "http://127.0.0.1:7890"
    
    # 示例1: 获取原始JSON数据
    print("=" * 60)
    print("示例1: 获取原始JSON数据")
    print("=" * 60)
    result = get_topics_news(topics_id=447, page=3, proxy=proxy)
    if result:
        print(json.dumps(result, indent=2, ensure_ascii=False)[:500] + "...")
    
    # 示例2: 打印格式化的股票信息
    print("\n" + "=" * 60)
    print("示例2: 打印格式化的股票信息")
    print("=" * 60)
    print_stock_info(topics_id=447, page=3, proxy=proxy)
    
    # 示例3: 获取多页数据
    print("\n" + "=" * 60)
    print("示例3: 获取第1-3页数据")
    print("=" * 60)
    for page in range(1, 4):
        print(f"\n>>> 第 {page} 页:")
        stocks = get_stock_data(topics_id=447, page=page, proxy=proxy)
        if stocks:
            print(f"获取到 {len(stocks)} 条数据")


if __name__ == "__main__":
    main()