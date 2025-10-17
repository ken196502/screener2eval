import React from 'react'
import { Card } from '@/components/ui/card'
import { Pie } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend
} from 'chart.js'

ChartJS.register(ArcElement, Tooltip, Legend)

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
  const formatCurrency = (amount: number) => {
    return `$${amount.toLocaleString('en-US', { 
      minimumFractionDigits: 2, 
      maximumFractionDigits: 2 
    })}`
  }

  // PnL should be based on total assets (cash + positions value)
  const pnl = totalAssets - user.initial_capital
  const pnlPercent = (pnl / user.initial_capital) * 100

  // Pie chart data
  const chartData = {
    labels: ['Positions Value', 'Available Cash', 'Frozen Cash'],
    datasets: [
      {
        data: [positionsValue, user.current_cash, user.frozen_cash],
        backgroundColor: [
          '#10b981', // green for positions
          '#3b82f6', // blue for available cash
          '#f59e0b'  // orange for frozen cash
        ],
        borderColor: [
          '#059669',
          '#2563eb',
          '#d97706'
        ],
        borderWidth: 2,
        hoverBackgroundColor: [
          '#059669',
          '#2563eb',
          '#d97706'
        ]
      }
    ]
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'right' as const,
        align: 'center' as const,
        labels: {
          padding: 15,
          usePointStyle: true,
          font: {
            size: 11
          },
          boxWidth: 12,
          boxHeight: 12
        }
      },
      tooltip: {
        callbacks: {
          label: function(context: any) {
            const label = context.label || ''
            const value = formatCurrency(context.parsed)
            const total = context.dataset.data.reduce((a: number, b: number) => a + b, 0)
            const percentage = ((context.parsed / total) * 100).toFixed(1)
            return `${label}: ${value} (${percentage}%)`
          }
        }
      }
    }
  }

  return (
    <div className="space-y-6">
      {/* Portfolio Overview Block */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Total Assets & Initial Capital */}
        <Card className="p-4">
          <div className="text-sm text-muted-foreground mb-1">Total Assets</div>
          <div className="text-2xl font-bold text-primary mb-2">
            {formatCurrency(totalAssets)}
          </div>
          <div className="text-xs text-muted-foreground">Initial Capital</div>
          <div className="text-sm font-medium text-muted-foreground">
            {formatCurrency(user.initial_capital)}
          </div>
          <div className={`text-sm font-medium mt-2 ${
            pnl >= 0 ? 'text-green-500' : 'text-destructive'
          }`}>
            {pnl >= 0 ? '+' : ''}{formatCurrency(pnl)} ({pnl >= 0 ? '+' : ''}{pnlPercent.toFixed(2)}%)
          </div>
        </Card>
        
        {/* Asset Distribution Pie Chart */}
        <Card className="p-4">
          <div className="text-sm text-muted-foreground mb-3">Asset Distribution</div>
          <div className="h-32 flex items-center justify-center">
            <div className="w-1/2 h-full mx-auto">
              <Pie data={chartData} options={chartOptions} />
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}