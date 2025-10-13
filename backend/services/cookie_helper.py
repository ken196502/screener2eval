"""
雪球Cookie获取帮助工具
"""

def get_required_cookies():
    """返回雪球API所需的关键cookie列表"""
    return [
        'xq_a_token',      # 访问令牌
        'xqat',            # 访问令牌别名
        'xq_r_token',      # 刷新令牌
        'xq_id_token',     # ID令牌
        'u',               # 用户ID
        'device_id',       # 设备ID
        'cookiesu',        # 用户Cookie
        'bid',             # 浏览器ID
        'xq_is_login',     # 登录状态
        'HMACCOUNT',       # 账户标识
        'Hm_lvt_*',        # 百度统计
        'Hm_lpvt_*',       # 百度统计
        'ssxmod_itna*',    # 会话相关
    ]

def validate_cookie_string(cookie_string: str) -> dict:
    """
    验证cookie字符串是否包含必要的认证信息
    
    Args:
        cookie_string: cookie字符串
        
    Returns:
        验证结果字典
    """
    if not cookie_string or not cookie_string.strip():
        return {
            "valid": False,
            "message": "Cookie字符串为空",
            "missing_cookies": get_required_cookies()
        }
    
    # 解析cookie
    cookies = {}
    for cookie in cookie_string.split(';'):
        if '=' in cookie:
            key, value = cookie.split('=', 1)
            cookies[key.strip()] = value.strip()
    
    # 检查必需的cookie
    required = ['xq_a_token', 'xqat', 'u', 'device_id']
    missing = []
    present = []
    
    for req in required:
        if req in cookies and cookies[req]:
            present.append(req)
        else:
            missing.append(req)
    
    is_valid = len(missing) == 0
    
    return {
        "valid": is_valid,
        "total_cookies": len(cookies),
        "present_required": present,
        "missing_required": missing,
        "all_cookies": list(cookies.keys()),
        "message": "Cookie验证通过" if is_valid else f"缺少必需的cookie: {', '.join(missing)}"
    }

def get_cookie_instructions():
    """返回获取雪球cookie的详细说明"""
    return """
获取雪球Cookie的步骤：

1. 打开Chrome或Edge浏览器
2. 访问 https://xueqiu.com 并登录您的账户
3. 按F12打开开发者工具
4. 切换到 Network (网络) 标签页
5. 在雪球网站上随便点击一个股票或刷新页面
6. 在Network标签页中找到任意一个对 stock.xueqiu.com 的请求
7. 点击该请求，在右侧面板中找到 Request Headers (请求头)
8. 复制 Cookie 字段的完整值

重要提示：
- 确保您已经登录雪球账户
- Cookie必须包含 xq_a_token, xqat, u, device_id 等关键字段
- Cookie会定期过期，需要重新获取
- 不要分享您的Cookie给他人，这等同于分享您的登录凭证

示例Cookie格式：
xq_a_token=abc123;xqat=abc123;u=12345;device_id=xyz789;...
"""