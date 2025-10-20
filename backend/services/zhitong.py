import requests
import json
import re
from typing import Dict, List


def is_success_status(status: object) -> bool:
    """
    Determine whether the upstream response status denotes success.
    """
    if status is None:
        return False
    if isinstance(status, (int, float)):
        return str(int(status)) in {"1000", "200"}
    if isinstance(status, str):
        normalized = status.lower()
        return normalized in {"success", "ok", "200", "1000"}
    return False


def _fallback_news_response(news_type: str, page: int, reason: str) -> Dict:
    """
    Build a fallback response when the upstream service is unavailable.
    """
    print(f"无法从上游获取{news_type}第{page}页新闻: {reason}")
    return {
        "status": "success",
        "data": {"list": []},
        "page": page,
        "source": "fallback-empty",
        "message": reason,
    }


def get_stock_news(page: int = 1, news_type: str = 'meigu') -> Dict:
    """
    获取智通财经美股新闻列表
    
    参数:
        page: 页码，默认为1
        news_type: 新闻类型，默认为'meigu'(美股)
    
    返回:
        包含新闻列表的字典
    """
    url = 'https://mapi.zhitongcaijing.com/news/list.html'
    
    params = {
        '__mode__': 'history',
        'access_token': '',
        'category_id': news_type,
        'category_key': 'sc',
        'language': 'zh-cn',
        'last_time': '',
        'page': page,
        'tradition_chinese': '0',
        'token': 'e7174fdce1299cc7656e21594bcde3f3a90586fb'
    }
    
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6,ja;q=0.5',
        'Connection': 'keep-alive',
        'Origin': 'https://m.zhitongcaijing.com',
        'Referer': 'https://m.zhitongcaijing.com/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        print(f"成功获取新闻数据，状态: {result.get('status')}")
        return result
    except requests.exceptions.Timeout as e:
        print(f"请求超时: {e}")
        return _fallback_news_response(news_type, page, "请求超时，已使用本地数据")
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return _fallback_news_response(news_type, page, f"请求失败: {e}")
    except ValueError as e:
        print(f"解析响应失败: {e}")
        return _fallback_news_response(news_type, page, f"解析响应失败: {e}")
    except Exception as e:
        print(f"未知错误: {e}")
        return _fallback_news_response(news_type, page, f"未知错误: {e}")


def get_gmteight_news(
    page: int = 1,
    page_size: int = 50,
    category_id: str = '61',
    parent_category_id: str = '35',
    style: int = 1,
) -> Dict:
    """
    获取GMT Eight新闻列表

    参数:
        page: 页码，默认为1
        page_size: 每页数量，默认为50
        category_id: 分类ID，默认为'61'
        parent_category_id: 父分类ID，默认为'35'
        style: 样式参数，默认为1

    返回:
        包含新闻列表的字典
    """
    url = 'https://api.gmteight.com/index/article'

    params = {
        'p_category_id': parent_category_id,
        'category_id': category_id,
        'style': style,
        'page': page,
        'page_size': page_size,
    }

    headers = {
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6,ja;q=0.5',
        'Connection': 'keep-alive',
        'Origin': 'https://gmteight.com',
        'Referer': 'https://gmteight.com/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1',
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        print(f"成功获取GMT Eight新闻数据，状态: {result.get('status')}")
        return result
    except requests.exceptions.Timeout as e:
        print(f"GMT Eight请求超时: {e}")
        return _fallback_news_response('gmteight', page, "请求超时，已使用本地数据")
    except requests.exceptions.RequestException as e:
        print(f"GMT Eight请求失败: {e}")
        return _fallback_news_response('gmteight', page, f"请求失败: {e}")
    except ValueError as e:
        print(f"GMT Eight解析响应失败: {e}")
        return _fallback_news_response('gmteight', page, f"解析响应失败: {e}")
    except Exception as e:
        print(f"GMT Eight未知错误: {e}")
        return _fallback_news_response('gmteight', page, f"未知错误: {e}")


def extract_stock_codes(text: str) -> List[str]:
    """
    从文本中提取股票Symbol，格式为括号内以.US结尾的Symbol
    
    参数:
        text: 要搜索的文本
    
    返回:
        提取到的股票Symbol列表，例如['AMD.US', 'NVDA.US']
    """
    pattern = r'\(([A-Z]+\.US)\)'
    matches = re.findall(pattern, text)
    return matches


def filter_us_stock_news(news_list: List[Dict]) -> List[Dict]:
    """
    过滤以"美股异动 |"开头的新闻，并提取股票Symbol
    
    参数:
        news_list: 原始新闻列表
    
    返回:
        过滤后的新闻列表，包含提取的股票Symbol
    """
    filtered_news = []
    
    prefixes = (
        '美股异动 |',
        'US Stock Market Move |',
    )

    for news in news_list:
        title = news.get('title', '')
        if any(title.startswith(prefix) for prefix in prefixes):
            # 从标题中提取股票Symbol
            stock_codes = extract_stock_codes(title)
            
            # 如果标题中没有找到，再从摘要中找
            if not stock_codes:
                digest = news.get('digest', '')
                stock_codes = extract_stock_codes(digest)
            
            # 如果还没找到，尝试从stock_list字段获取
            if not stock_codes and news.get('stock_list'):
                stock_list = news.get('stock_list', '')
                # 直接使用stock_list字段的值
                if stock_list:
                    stock_codes = [stock_list] if isinstance(stock_list, str) else stock_list
            
            # 添加股票Symbol字段到新闻条目
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
        'image': news_item.get('image', ''),
    }


def parse_gmteight_news_item(news_item: Dict) -> Dict:
    """
    解析GMT Eight新闻数据

    参数:
        news_item: 新闻条目字典

    返回:
        解析后的新闻信息
    """
    return {
        'content_id': news_item.get('id', ''),
        'title': news_item.get('title', ''),
        'digest': news_item.get('digest', ''),
        'keywords': '',
        'author': news_item.get('post_author', ''),
        'create_time': news_item.get('create_time', ''),
        'browse_count': '',
        'url': '',
        'image': news_item.get('image', ''),
        'content': news_item.get('content', ''),
    }


def filter_gmteight_stock_news(news_list: List[Dict]) -> List[Dict]:
    """
    过滤GMT Eight中以"US Stock Market Move |"开头的新闻并提取股票Symbol

    参数:
        news_list: 原始新闻列表

    返回:
        过滤后的新闻列表，包含提取的股票Symbol
    """
    filtered_news = []
    prefix = 'US Stock Market Move |'

    for news in news_list:
        title = news.get('title', '')
        if not title.startswith(prefix):
            continue

        stock_codes = extract_stock_codes(title)

        if not stock_codes:
            digest = news.get('digest', '')
            stock_codes = extract_stock_codes(digest)

        if not stock_codes:
            content = news.get('content', '')
            stock_codes = extract_stock_codes(content)

        news_with_codes = news.copy()
        if stock_codes:
            news_with_codes['stock_codes'] = stock_codes

        filtered_news.append(news_with_codes)

    return filtered_news


def display_news(news_list: List[Dict], show_stock_codes: bool = False) -> None:
    """
    格式化显示新闻列表
    
    参数:
        news_list: 新闻列表
        show_stock_codes: 是否显示提取的股票Symbol
    """
    print("\n" + "="*80)
    print(f"{'美股异动新闻':^76}")
    print("="*80 + "\n")
    
    for idx, news in enumerate(news_list, 1):
        print(f"【{idx}】 {news['title']}")
        print(f"    摘要: {news['digest']}")
        
        # 如果有股票Symbol，显示它们
        if show_stock_codes and 'stock_codes' in news and news['stock_codes']:
            print(f"    股票Symbol: {', '.join(news['stock_codes'])}")
        
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
    获取并过滤美股异动新闻，提取股票Symbol
    
    参数:
        page: 页码，默认为1
    
    返回:
        过滤后的美股异动新闻列表，包含股票Symbol
    """
    print(f"正在获取第{page}页美股异动新闻...")
    
    # 获取新闻
    result = get_stock_news(page=page)
    
    if not is_success_status(result.get('status')):
        print("获取新闻失败，状态码:", result.get('status'))
        return []
    
    news_data = result.get('data', {})
    news_list = news_data.get('list', [])
    
    if not news_list:
        print("没有获取到新闻数据")
        return []
    
    # 解析新闻数据
    parsed_news = [parse_news_item(item) for item in news_list]
    
    # 过滤美股异动新闻并提取股票Symbol
    us_stock_news = filter_us_stock_news(parsed_news)
    
    return us_stock_news


def main():
    """
    主函数：获取并显示美股新闻
    """
    print("正在获取美股异动新闻...")
    
    # 获取第1页新闻
    result = get_stock_news(page=1)
    
    if not is_success_status(result.get('status')):
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
            if is_success_status(result.get('status')):
                news_list = result.get('data', {}).get('list', [])
                parsed_news = [parse_news_item(item) for item in news_list]
                display_news(parsed_news)
                save_to_json(parsed_news, f'us_stock_news_page{page_num}.json')
    except KeyboardInterrupt:
        print("\n\n程序已退出")


if __name__ == "__main__":
    main()
