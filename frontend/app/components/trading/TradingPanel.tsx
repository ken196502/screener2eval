import React, { useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select'
import { toast } from 'react-hot-toast'

interface User {
  current_cash: number
  frozen_cash: number
  has_password: boolean
}

interface PositionLite { symbol: string; market: string; available_quantity: number }

interface TradingPanelProps {
  onPlace: (payload: any) => void
  user?: User
  positions?: PositionLite[]
  lastPrices?: Record<string, number | null>
}

export default function TradingPanel({ onPlace, user, positions = [], lastPrices = {} }: TradingPanelProps) {
  const [symbol, setSymbol] = useState('AAPL')
  const [name, setName] = useState('Apple Inc.')
  const [market] = useState<'US'>('US')
  const [orderType, setOrderType] = useState<'MARKET' | 'LIMIT'>('LIMIT')
  const [price, setPrice] = useState<number>(190)

  // 当切换到 MARKET，价格从 WS/父组件传入的最新行情刷新
  const onSelectOrderType = (v: 'MARKET' | 'LIMIT') => {
    setOrderType(v)
    if (v === 'MARKET') {
      const lp = lastPrices[`${symbol}.${market}`]
      if (lp && Number.isFinite(lp)) {
        setPrice(Math.round(lp * 100) / 100)
      }
      toast('Using market price from server', { icon: '💹' })
    }
  }

  // 市价模式下，随 WS 推送的最新价自动刷新显示价格
  useEffect(() => {
    if (orderType !== 'MARKET') return
    const lp = lastPrices[`${symbol}.${market}`]
    if (lp && Number.isFinite(lp)) {
      setPrice(Math.round(lp * 100) / 100)
    }
  }, [orderType, lastPrices, symbol, market])
  const [quantity, setQuantity] = useState<number>(2)
  const [showPasswordDialog, setShowPasswordDialog] = useState<boolean>(false)
  const [pendingTrade, setPendingTrade] = useState<{side: 'BUY' | 'SELL'} | null>(null)
  const [dialogPassword, setDialogPassword] = useState<string>('')
  const [dialogUsername, setDialogUsername] = useState<string>('')
  const [authSessionToken, setAuthSessionToken] = useState<string>('')
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false)
  const [authExpiry, setAuthExpiry] = useState<string>('')

  // US market only - USD currency
  const currencySymbol = '$'

  // Check if user has valid auth session on component mount
  useEffect(() => {
    const savedToken = localStorage.getItem(`auth_session_${user?.id}`)
    const savedExpiry = localStorage.getItem(`auth_expiry_${user?.id}`)
    
    if (savedToken && savedExpiry && user?.id) {
      const expiryDate = new Date(savedExpiry)
      if (expiryDate > new Date()) {
        // Verify token with backend
        verifyAuthSession(savedToken)
      } else {
        // Token expired, clear storage
        clearAuthSession()
      }
    }
  }, [user?.id])

  const verifyAuthSession = async (token: string) => {
    try {
      const response = await fetch('/api/account/auth/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_token: token })
      })
      const data = await response.json()
      
      if (data.valid && data.user_id === user?.id) {
        setAuthSessionToken(token)
        setIsAuthenticated(true)
        const savedExpiry = localStorage.getItem(`auth_expiry_${user?.id}`)
        if (savedExpiry) {
          setAuthExpiry(savedExpiry)
        }
      } else {
        clearAuthSession()
      }
    } catch (error) {
      console.error('Failed to verify auth session:', error)
      clearAuthSession()
    }
  }

  const clearAuthSession = () => {
    setAuthSessionToken('')
    setIsAuthenticated(false)
    setAuthExpiry('')
    if (user?.id) {
      localStorage.removeItem(`auth_session_${user.id}`)
      localStorage.removeItem(`auth_expiry_${user.id}`)
    }
  }


  const handlePasswordSubmit = async () => {
    if (!dialogPassword.trim()) {
      toast.error('Please enter trading password')
      return
    }

    if (!dialogUsername.trim()) {
      toast.error('Please enter username')
      return
    }

    if (!pendingTrade) return

    try {
      // 写死功能：认证成功后自动创建180天免密会话
      const response = await fetch(`/api/account/auth/login?user_id=${user?.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          username: dialogUsername, 
          password: dialogPassword 
        })
      })
      const data = await response.json()
      
      if (response.ok) {
        // 保存180天认证会话
        setAuthSessionToken(data.session_token)
        setIsAuthenticated(true)
        setAuthExpiry(data.expires_at)
        
        // 保存到本地存储
        if (user?.id) {
          localStorage.setItem(`auth_session_${user.id}`, data.session_token)
          localStorage.setItem(`auth_expiry_${user.id}`, data.expires_at)
        }
        
        toast.success('认证成功，180天内免密交易')
        
        // 使用session token执行交易
        const orderData: any = {
          symbol,
          name,
          market,
          side: pendingTrade.side,
          order_type: orderType,
          price: orderType === 'LIMIT' ? price : undefined,
          quantity,
          session_token: data.session_token
        }

        onPlace(orderData)
      } else {
        toast.error(data.detail || '用户名或密码错误')
      }
    } catch (error) {
      console.error('Failed to authenticate:', error)
      toast.error('认证失败，请重试')
    } finally {
      // Close dialog and reset state
      setShowPasswordDialog(false)
      setPendingTrade(null)
      setDialogPassword('')
      setDialogUsername('')
    }
  }

  const adjustPrice = (delta: number) => {
    if (orderType === 'MARKET') return // 市价单不允许手动改价
    const newPrice = Math.max(0, price + delta)
    setPrice(Math.round(newPrice * 100) / 100) // 保证两位小数
  }

  const handlePriceChange = (value: string) => {
    if (orderType === 'MARKET') return // 市价单不允许手动改价
    // 只允许数字和一个小数点
    if (!/^\d*\.?\d{0,2}$/.test(value)) return
    
    const numValue = parseFloat(value) || 0
    setPrice(numValue)
  }

  const adjustQuantity = (delta: number) => {
    setQuantity(Math.max(0, quantity + delta))
  }

  const amount = price * quantity
  const cashAvailable = user?.current_cash ?? 0
  const frozenCash = user?.frozen_cash ?? 0
  const availableCash = Math.max(cashAvailable - frozenCash, 0)
  const positionAvailable = useMemo(() => {
    const p = positions.find(p => p.symbol === symbol && p.market === market)
    return p?.available_quantity || 0
  }, [positions, symbol, market])
  const effectivePrice = orderType === 'MARKET' ? (lastPrices[`${symbol}.${market}`] ?? price) : price
  const maxBuyable = Math.floor(availableCash / Math.max(effectivePrice || 0, 0.0001)) || 0

  const handleBuy = () => {
    if (orderType === 'LIMIT' && price <= 0) {
      toast.error('Please input a valid limit price')
      return
    }
    if (quantity <= 0 || !Number.isFinite(quantity)) {
      toast.error('Please input a valid quantity')
      return
    }
    if (amount > cashAvailable) {
      toast.error('Insufficient available cash')
      return
    }
    
    // 如果已认证，直接交易
    if (isAuthenticated && authSessionToken) {
      const orderData: any = {
        symbol,
        name,
        market,
        side: 'BUY',
        order_type: orderType,
        price: orderType === 'LIMIT' ? price : undefined,
        quantity,
        session_token: authSessionToken
      }
      onPlace(orderData)
    } else {
      // 未认证，显示密码弹窗
      setPendingTrade({side: 'BUY'})
      setShowPasswordDialog(true)
    }
  }

  const handleSell = () => {
    if (orderType === 'LIMIT' && price <= 0) {
      toast.error('Please input a valid limit price')
      return
    }
    if (quantity <= 0 || !Number.isFinite(quantity)) {
      toast.error('Please input a valid quantity')
      return
    }
    if (quantity > positionAvailable) {
      toast.error('Insufficient sellable position')
      return
    }
    
    // 如果已认证，直接交易
    if (isAuthenticated && authSessionToken) {
      const orderData: any = {
        symbol,
        name,
        market,
        side: 'SELL',
        order_type: orderType,
        price: orderType === 'LIMIT' ? price : undefined,
        quantity,
        session_token: authSessionToken
      }
      onPlace(orderData)
    } else {
      // 未认证，显示密码弹窗
      setPendingTrade({side: 'SELL'})
      setShowPasswordDialog(true)
    }
  }

  return (
    <div className="space-y-4 w-[320px] flex-shrink-0">
      {/* Symbol */}
      <div className="space-y-2">
        <label className="text-xs">Code</label>
        <div className="relative">
          <Input 
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
          />
        </div>
        <div className="text-xs text-muted-foreground">{name}</div>
      </div>

      {/* 订单类型 */}
      <div className="space-y-2">
        <div className="flex items-center gap-1">
          <label className="text-xs text-muted-foreground">Order Type</label>
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-info w-3 h-3 text-muted-foreground">
            <circle cx="12" cy="12" r="10"></circle>
            <path d="M12 16v-4"></path>
            <path d="M12 8h.01"></path>
          </svg>
        </div>
        <Select value={orderType} onValueChange={(v) => onSelectOrderType(v as 'MARKET' | 'LIMIT')}>
          <SelectTrigger className="bg-input text-xs h-6">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="LIMIT">Limit Order</SelectItem>
            <SelectItem value="MARKET">Market Order</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* 价格 */}
      <div className="space-y-2">
        <label className="text-xs">Price</label>
        <div className="flex items-center gap-2">
         <Button 
            onClick={() => adjustPrice(-0.01)}
            variant="outline"
            disabled={orderType === 'MARKET'}
          >
            -
          </Button>
          <div className="relative flex-1">
           <Input 
              inputMode="decimal"
              value={price.toString()}
              onChange={(e) => handlePriceChange(e.target.value)}
              className="text-center"
              disabled={orderType === 'MARKET'}
            />
          </div>
         <Button 
            onClick={() => adjustPrice(0.01)}
            variant="outline"
            disabled={orderType === 'MARKET'}
          >
            +
          </Button>
        </div>
      </div>

      {/* 数量 */}
      <div className="space-y-2">
        <label className="text-xs">Quantity</label>
        <div className="flex items-center gap-2">
          <Button 
            onClick={() => adjustQuantity(-1)}
            variant="outline"
          >
            -
          </Button>
          <div className="relative flex-1">
            <Input 
              inputMode="numeric"
              value={quantity}
              onChange={(e) => setQuantity(parseInt(e.target.value) || 0)}
              className="text-center"
            />
          </div>
          <Button 
            onClick={() => adjustQuantity(1)}
            variant="outline"
          >
            +
          </Button>
        </div>
      </div>

      {/* 交易信息 */}
      <div className="space-y-3 pt-4">
        <div className="flex justify-between">
          <span className="text-xs">Amount</span>
          <span className="text-xs">{currencySymbol}{amount.toFixed(2)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-xs">Available Cash</span>
          <span className="text-xs text-green-500">{currencySymbol}{cashAvailable.toFixed(2)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-xs">Frozen Cash</span>
          <span className="text-xs text-orange-500">{currencySymbol}{frozenCash.toFixed(2)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-xs">Sellable Position</span>
          <span className="text-xs text-destructive">{positionAvailable}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-xs">Max Buyable</span>
          <span className="text-xs">{maxBuyable} shares</span>
        </div>
      </div>


      {/* 买卖按钮 */}
      <div className="flex gap-2 pt-4">
        <Button 
          className="flex-1 text-xs h-6 rounded-xl bg-destructive hover:bg-destructive/90 text-destructive-foreground"
          onClick={handleBuy}
        >
          Buy
        </Button>
        <Button 
          className="flex-1 text-xs h-6 rounded-xl bg-green-600 hover:bg-green-500 text-white"
          onClick={handleSell}
        >
          Sell
        </Button>
      </div>

      {/* 密码输入弹窗 */}
      {showPasswordDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-background rounded-lg p-6 w-80 max-w-sm mx-4">
            <h3 className="text-lg font-semibold mb-4">
              确认交易 - {pendingTrade?.side === 'BUY' ? '买入' : '卖出'}
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  用户名
                </label>
                <Input
                  type="text"
                  value={dialogUsername}
                  onChange={(e) => setDialogUsername(e.target.value)}
                  placeholder="输入用户名"
                  className="w-full"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  交易密码
                </label>
                <Input
                  type="password"
                  value={dialogPassword}
                  onChange={(e) => setDialogPassword(e.target.value)}
                  placeholder={user?.has_password ? "输入交易密码" : "设置新的交易密码"}
                  className="w-full"
                />
                <div className="text-xs text-gray-500 mt-1">
                  {user?.has_password 
                    ? "输入已设置的交易密码" 
                    : "首次交易将设置此密码为交易密码"
                  }
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowPasswordDialog(false)
                    setPendingTrade(null)
                    setDialogPassword('')
                    setDialogUsername('')
                  }}
                  className="flex-1"
                >
                  取消
                </Button>
                <Button
                  onClick={handlePasswordSubmit}
                  disabled={!dialogPassword.trim() || !dialogUsername.trim()}
                  className="flex-1"
                >
                  确认交易
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}