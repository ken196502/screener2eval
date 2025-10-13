import requests
import json
import re
from typing import Dict, List, Optional
from datetime import datetime


def get_stock_news(page: int = 1, news_type: str = 'meigu') -> Dict:
    """
    获取智通财经美股新闻列表
    
    参数:
        page: 页码，默认为1
        news_type: 新闻类型，默认为'meigu'(美股)
    
    返回:
        包含新闻列表的字典
    """
    url = 'https://m.zhitongcaijing.com/content/get-content-list.html'
    
    params = {
        'page': page,
        'type': news_type
    }
    
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6,ja;q=0.5',
        'Connection': 'keep-alive',
        'Referer': 'https://m.zhitongcaijing.com/content/meigu.html',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return {}


def extract_stock_codes(text: str) -> List[str]:
    """
    从文本中提取股票代码，格式为括号内以.US结尾的代码
    
    参数:
        text: 要搜索的文本
    
    返回:
        提取到的股票代码列表，例如['AMD.US', 'NVDA.US']
    """
    pattern = r'\(([A-Z]+\.US)\)'
    matches = re.findall(pattern, text)
    return matches


def filter_us_stock_news(news_list: List[Dict]) -> List[Dict]:
    """
    过滤以"美股异动 |"开头的新闻，并提取股票代码
    
    参数:
        news_list: 原始新闻列表
    
    返回:
        过滤后的新闻列表，包含提取的股票代码
    """
    filtered_news = []
    
    for news in news_list:
        digest = news.get('digest', '')
        if digest.startswith('美股异动 |'):
            # 提取股票代码
            stock_codes = extract_stock_codes(digest)
            
            # 添加股票代码字段到新闻条目
            news_with_codes = news.copy()
            news_with_codes['stock_codes'] = stock_codes
            
            filtered_news.append(news_with_codes)
    
    return filtered_news


def parse_news_item(news_item: Dict) -> Dict:
    """
    解析单条新闻数据，提取关键信息
    
    参数:
        news_item: 新闻条目字典
    
    返回:
        解析后的新闻信息
    """
    return {
        'content_id': news_item.get('content_id', ''),
        'title': news_item.get('title', ''),
        'digest': news_item.get('digest', ''),
        'keywords': news_item.get('keywords', ''),
        'author': news_item.get('author_name', ''),
        'create_time': news_item.get('create_time_desc', ''),
        'browse_count': news_item.get('browse_count', '0'),
        'url': news_item.get('url', ''),
        'image': news_item.get('image', '')
    }


def display_news(news_list: List[Dict], show_stock_codes: bool = False) -> None:
    """
    格式化显示新闻列表
    
    参数:
        news_list: 新闻列表
        show_stock_codes: 是否显示提取的股票代码
    """
    print("\n" + "="*80)
    print(f"{'美股异动新闻':^76}")
    print("="*80 + "\n")
    
    for idx, news in enumerate(news_list, 1):
        print(f"【{idx}】 {news['title']}")
        print(f"    摘要: {news['digest']}")
        
        # 如果有股票代码，显示它们
        if show_stock_codes and 'stock_codes' in news and news['stock_codes']:
            print(f"    股票代码: {', '.join(news['stock_codes'])}")
        
        print(f"    关键词: {news['keywords']}")
        print(f"    作者: {news['author']} | 时间: {news['create_time']} | 浏览: {news['browse_count']}")
        print(f"    链接: {news['url']}")
        print("-" * 80 + "\n")


def save_to_json(news_list: List[Dict], filename: str = 'us_stock_news.json') -> None:
    """
    将新闻数据保存为JSON文件
    
    参数:
        news_list: 新闻列表
        filename: 保存的文件名
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(news_list, f, ensure_ascii=False, indent=2)
        print(f"\n数据已保存到 {filename}")
    except Exception as e:
        print(f"保存文件失败: {e}")


def get_us_stock_movement_news(page: int = 1) -> List[Dict]:
    """
    获取并过滤美股异动新闻，提取股票代码
    
    参数:
        page: 页码，默认为1
    
    返回:
        过滤后的美股异动新闻列表，包含股票代码
    """
    print(f"正在获取第{page}页美股异动新闻...")
    
    # 获取新闻
    result = get_stock_news(page=page)
    
    if result.get('status') != 1000:
        print("获取新闻失败，状态码:", result.get('status'))
        return []
    
    news_data = result.get('data', {})
    news_list = news_data.get('list', [])
    
    if not news_list:
        print("没有获取到新闻数据")
        return []
    
    # 解析新闻数据
    parsed_news = [parse_news_item(item) for item in news_list]
    
    # 过滤美股异动新闻并提取股票代码
    us_stock_news = filter_us_stock_news(parsed_news)
    
    return us_stock_news


def main():
    """
    主函数：获取并显示美股新闻
    """
    print("正在获取美股异动新闻...")
    
    # 获取第1页新闻
    result = get_stock_news(page=1)
    
    if result.get('status') != 1000:
        print("获取新闻失败，状态码:", result.get('status'))
        return
    
    news_data = result.get('data', {})
    news_list = news_data.get('list', [])
    
    if not news_list:
        print("没有获取到新闻数据")
        return
    
    # 解析新闻数据
    parsed_news = [parse_news_item(item) for item in news_list]
    
    # 显示所有新闻
    display_news(parsed_news)
    
    # 过滤并显示美股异动新闻
    us_stock_news = filter_us_stock_news(parsed_news)
    
    if us_stock_news:
        print("\n" + "="*80)
        print(f"{'过滤后的美股异动新闻':^76}")
        print("="*80)
        display_news(us_stock_news, show_stock_codes=True)
        
        # 保存过滤后的新闻
        save_to_json(us_stock_news, 'us_stock_movement_news.json')
        print(f"\n过滤后共获取到 {len(us_stock_news)} 条美股异动新闻")
    else:
        print("\n没有找到美股异动新闻")
    
    # 保存所有新闻到文件
    save_to_json(parsed_news)
    
    print(f"\n总共获取到 {len(parsed_news)} 条新闻")
    
    # 询问是否获取更多页
    try:
        more_pages = input("\n是否获取更多页? (输入页码，或按Enter键退出): ").strip()
        if more_pages.isdigit():
            page_num = int(more_pages)
            result = get_stock_news(page=page_num)
            if result.get('status') == 1000:
                news_list = result.get('data', {}).get('list', [])
                parsed_news = [parse_news_item(item) for item in news_list]
                display_news(parsed_news)
                save_to_json(parsed_news, f'us_stock_news_page{page_num}.json')
    except KeyboardInterrupt:
        print("\n\n程序已退出")


if __name__ == "__main__":
    main()