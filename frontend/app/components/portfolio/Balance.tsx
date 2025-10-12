import React from 'react'
import { Card } from '@/components/ui/card'

interface User {
  initial_capital: number
  current_cash: number
  frozen_cash: number
}

interface BalanceProps {
  user: User
  totalAssets: number
  positionsValue: number
}

export default function Balance({ 
  user, 
  totalAssets, 
  positionsValue 
}: BalanceProps) {
  const formatCurrency = (amount: number) => {
    return `$${amount.toLocaleString('en-US', { 
      minimumFractionDigits: 2, 
      maximumFractionDigits: 2 
    })}`
  }

  const pnl = user.current_cash - user.initial_capital
  const pnlPercent = (pnl / user.initial_capital) * 100

  return (
    <div className="flex gap-4 w-full">
    <Card className="p-4 w-1/2">
      <div className="text-sm text-muted-foreground mb-1">Total Assets</div>
      <div className="text-2xl font-bold text-blue-600">
        {formatCurrency(totalAssets)}
      </div>
    </Card>
    <Card className="p-4 w-1/2">
      <div className="text-sm text-muted-foreground mb-1">Positions Value</div>
      <div className="text-2xl font-bold text-green-600">
        {formatCurrency(positionsValue)}
      </div>
    </Card>
  {/* Account Balance */}
  <Card className="p-4 w-full">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-medium text-base">
          US Stock Account
        </h4>
        <div className="text-right">
          <div className={`text-sm font-medium ${
            pnl >= 0 ? 'text-green-600' : 'text-red-600'
          }`}>
            {pnl >= 0 ? '+' : ''}{formatCurrency(pnl)}
          </div>
          <div className={`text-xs ${
            pnl >= 0 ? 'text-green-600' : 'text-red-600'
          }`}>
            {pnl >= 0 ? '+' : ''}{pnlPercent.toFixed(2)}%
          </div>
        </div>
      </div>
      
      <div className="grid grid-cols-3 gap-4 text-sm">
        <div>
          <div className="text-muted-foreground mb-1">Available Cash</div>
          <div className="font-medium">
            {formatCurrency(user.current_cash)}
          </div>
        </div>
        <div>
          <div className="text-muted-foreground mb-1">Frozen Cash</div>
          <div className="font-medium text-orange-600">
            {formatCurrency(user.frozen_cash)}
          </div>
        </div>
        <div>
          <div className="text-muted-foreground mb-1">Initial Capital</div>
          <div className="font-medium text-gray-600">
            {formatCurrency(user.initial_capital)}
          </div>
        </div>
      </div>
      
      {/* Progress bar for cash usage */}
      <div className="mt-3">
        <div className="flex justify-between text-xs text-muted-foreground mb-1">
          <span>Cash Usage</span>
          <span>
            {((user.initial_capital - user.current_cash) / user.initial_capital * 100).toFixed(1)}%
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className="bg-blue-500 h-2 rounded-full transition-all duration-300"
            style={{ 
              width: `${Math.min(100, (user.initial_capital - user.current_cash) / user.initial_capital * 100)}%` 
            }}
          />
        </div>
      </div>
    </Card>
  </div>
  )
}