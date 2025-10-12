import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select'

interface User {
  current_cash: number
  frozen_cash: number
}

interface TradingPanelProps {
  onPlace: (payload: any) => void
  user?: User
}

export default function TradingPanel({ onPlace, user }: TradingPanelProps) {
  const [symbol, setSymbol] = useState('AAPL')
  const [name, setName] = useState('Apple Inc.')
  const [market] = useState<'US'>('US')
  const [orderType, setOrderType] = useState<'MARKET' | 'LIMIT'>('LIMIT')
  const [price, setPrice] = useState<number>(190)
  const [quantity, setQuantity] = useState<number>(2)

  // US market only - USD currency
  const currencySymbol = '$'

  const adjustPrice = (delta: number) => {
    const newPrice = Math.max(0, price + delta)
    setPrice(Math.round(newPrice * 100) / 100) // 保证两位小数
  }

  const handlePriceChange = (value: string) => {
    // 只允许数字和一个小数点
    if (!/^\d*\.?\d{0,2}$/.test(value)) return
    
    const numValue = parseFloat(value) || 0
    setPrice(numValue)
  }

  const adjustQuantity = (delta: number) => {
    setQuantity(Math.max(0, quantity + delta))
  }

  const amount = price * quantity
  const cashAvailable = user?.current_cash || 0
  const frozenCash = user?.frozen_cash || 0
  const positionAvailable = 0 // TODO: Calculate from position data
  const maxBuyable = Math.floor(cashAvailable / price) || 0

  const handleBuy = () => {
    onPlace({
      symbol,
      name,
      market,
      side: 'BUY',
      order_type: orderType,
      price: orderType === 'LIMIT' ? price : undefined,
      quantity
    })
  }

  const handleSell = () => {
    onPlace({
      symbol,
      name,
      market,
      side: 'SELL',
      order_type: orderType,
      price: orderType === 'LIMIT' ? price : undefined,
      quantity
    })
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
        <Select value={orderType} onValueChange={(v) => setOrderType(v as 'MARKET' | 'LIMIT')}>
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
          >
            -
          </Button>
          <div className="relative flex-1">
            <Input 
              inputMode="decimal"
              value={price.toString()}
              onChange={(e) => handlePriceChange(e.target.value)}
              className="text-center"
            />
          </div>
          <Button 
            onClick={() => adjustPrice(0.01)}
            variant="outline"
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
          <span className="text-xs text-[#16BA71]">{currencySymbol}{cashAvailable.toFixed(2)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-xs">Frozen Cash</span>
          <span className="text-xs text-orange-500">{currencySymbol}{frozenCash.toFixed(2)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-xs">Sellable Position</span>
          <span className="text-xs text-[#F44345]">{positionAvailable}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-xs">Max Buyable</span>
          <span className="text-xs">{maxBuyable} shares</span>
        </div>
      </div>

      {/* 买卖按钮 */}
      <div className="flex gap-2 pt-4">
        <Button 
          className="flex-1 text-xs h-6 rounded-xl bg-[#F44345] hover:bg-[#d63b3d] text-white"
          onClick={handleBuy}
        >
          Buy
        </Button>
        <Button 
          className="flex-1 text-xs h-6 rounded-xl bg-[#16BA71] hover:bg-[#10975c] text-white"
          onClick={handleSell}
        >
          Sell
        </Button>
      </div>
    </div>
  )
}