import requests
import json
from typing import Dict, List
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


def display_news(news_list: List[Dict]) -> None:
    """
    格式化显示新闻列表
    
    参数:
        news_list: 新闻列表
    """
    print("\n" + "="*80)
    print(f"{'美股异动新闻':^76}")
    print("="*80 + "\n")
    
    for idx, news in enumerate(news_list, 1):
        print(f"【{idx}】 {news['title']}")
        print(f"    摘要: {news['digest']}")
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
    
    # 显示新闻
    display_news(parsed_news)
    
    # 保存到文件
    save_to_json(parsed_news)
    
    print(f"\n共获取到 {len(parsed_news)} 条新闻")
    
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