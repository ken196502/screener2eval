import React from 'react'
import Balance from './Balance'
import NetValueChart from './NetValueChart'
import { Card } from '@/components/ui/card'

interface User {
  id: number
  username: string
  initial_capital: number
  current_cash: number
  frozen_cash: number
}

interface PortfolioProps {
  user: User
  totalAssets: number
  positionsValue: number
}

export default function Portfolio({ 
  user, 
  totalAssets, 
  positionsValue 
}: PortfolioProps) {
  return (
    <div className="space-y-6">
      {/* Portfolio Overview Block */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Balance Block */}
        <div>
          <Balance 
            user={user}
            totalAssets={totalAssets}
            positionsValue={positionsValue}
          />
        </div>
      </div>
    </div>
  )
}

