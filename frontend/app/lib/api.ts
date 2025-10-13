// API configuration
const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? '/api' 
  : '/api'  // 使用代理，不要硬编码端口

// Helper function for making API requests
export async function apiRequest(
  endpoint: string, 
  options: RequestInit = {}
): Promise<Response> {
  const url = `${API_BASE_URL}${endpoint}`
  
  const defaultOptions: RequestInit = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  }
  
  const response = await fetch(url, defaultOptions)
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  
  const contentType = response.headers.get('content-type')
  if (!contentType || !contentType.includes('application/json')) {
    throw new Error('Response is not JSON')
  }
  
  return response
}

// Specific API functions
export async function checkRequiredConfigs() {
  const response = await apiRequest('/config/check-required')
  return response.json()
}

export async function getXueqiuCookie() {
  const response = await apiRequest('/config/xueqiu-cookie')
  return response.json()
}

export async function saveXueqiuCookie(cookieValue: string, description: string = '雪球API访问Cookie') {
  const response = await apiRequest('/config/xueqiu-cookie', {
    method: 'POST',
    body: JSON.stringify({
      key: 'xueqiu_cookie',
      value: cookieValue,
      description: description
    }),
  })
  return response.json()
}