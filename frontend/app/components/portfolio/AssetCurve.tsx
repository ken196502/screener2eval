import React, { useEffect, useState } from 'react'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions,
} from 'chart.js'
import { Card } from '@/components/ui/card'

// 注册Chart.js组件
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

interface AssetCurveData {
  date: string
  total_assets: number
  cash: number
  positions_value: number
  is_initial: boolean
}

const API_BASE = 'http://127.0.0.1:2611'

export default function AssetCurve() {
  const [data, setData] = useState<AssetCurveData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchAssetCurve()
  }, [])

  const fetchAssetCurve = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // 默认使用用户ID 1，在实际应用中应该从用户状态或路由参数获取
      const response = await fetch(`${API_BASE}/api/account/asset-curve?user_id=1`)
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      const assetData = await response.json()
      setData(assetData)
    } catch (err) {
      console.error('获取资产曲线失败:', err)
      setError(err instanceof Error ? err.message : '获取资产曲线失败')
    } finally {
      setLoading(false)
    }
  }

  const chartData = {
    labels: data.map(item => {
      const date = new Date(item.date)
      return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric' 
      })
    }),
    datasets: [
      {
        label: 'Total Assets',
        data: data.map(item => item.total_assets),
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.1,
      },
      {
        label: 'Cash',
        data: data.map(item => item.cash),
        borderColor: 'rgb(34, 197, 94)',
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
        borderWidth: 2,
        fill: false,
        tension: 0.1,
      },
      {
        label: 'Positions Value',
        data: data.map(item => item.positions_value),
        borderColor: 'rgb(168, 85, 247)',
        backgroundColor: 'rgba(168, 85, 247, 0.1)',
        borderWidth: 2,
        fill: false,
        tension: 0.1,
      },
    ],
  }

  const options: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: 'Asset Curve',
        font: {
          size: 16,
          weight: 'bold',
        },
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        callbacks: {
          label: (context) => {
            const label = context.dataset.label || ''
            const value = context.parsed.y
            return `${label}: $${value?.toLocaleString('en-US', { 
              minimumFractionDigits: 2, 
              maximumFractionDigits: 2 
            })}`
          },
        },
      },
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Date',
        },
      },
      y: {
        display: true,
        title: {
          display: true,
          text: 'Amount (USD)',
        },
        ticks: {
          callback: function(value) {
            return '$' + Number(value).toLocaleString('en-US')
          },
        },
      },
    },
    interaction: {
      mode: 'nearest',
      axis: 'x',
      intersect: false,
    },
  }

  if (loading) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center h-96">
          <div className="text-muted-foreground">Loading asset curve...</div>
        </div>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="p-6">
        <div className="flex flex-col items-center justify-center h-96 space-y-4">
          <div className="text-destructive">Failed to load asset curve: {error}</div>
          <button
            onClick={fetchAssetCurve}
            className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 transition-colors"
          >
            Retry
          </button>
        </div>
      </Card>
    )
  }

  if (data.length === 0) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center h-96">
          <div className="text-muted-foreground">No asset data available</div>
        </div>
      </Card>
    )
  }

  return (
    <Card className="p-6">
      <div className="h-96">
        <Line data={chartData} options={options} />
      </div>
      
      {/* 统计信息 */}
      <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-secondary p-4 rounded-lg">
          <div className="text-sm text-secondary-foreground font-medium">Current Total Assets</div>
          <div className="text-2xl font-bold text-secondary-foreground">
            $ {data[data.length - 1]?.total_assets.toLocaleString('en-US', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </div>
        </div>
        
        <div className="bg-secondary p-4 rounded-lg">
          <div className="text-sm text-secondary-foreground font-medium">Current Cash</div>
          <div className="text-2xl font-bold text-secondary-foreground">
            ${data[data.length - 1]?.cash.toLocaleString('en-US', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </div>
        </div>
        
        <div className="bg-secondary p-4 rounded-lg">
          <div className="text-sm text-secondary-foreground font-medium">Current Position Value</div>
          <div className="text-2xl font-bold text-secondary-foreground">
            ${data[data.length - 1]?.positions_value.toLocaleString('en-US', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </div>
        </div>
      </div>
    </Card>
  )
}