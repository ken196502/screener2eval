import React, { useState, useEffect, useRef, useMemo } from 'react'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { RefreshCw, TrendingUp, TrendingDown } from 'lucide-react'

declare global {
  interface Window {
    TradingView?: {
      widget: new (config: Record<string, unknown>) => unknown
    }
    __tradingViewScriptLoading?: boolean
  }
}

interface Factor {
  id: string
  name: string
  description: string
  columns: Array<{
    key: string
    label: string
    type: string
    sortable: boolean
  }>
}

interface FactorsResponse {
  success: boolean
  factors: Factor[]
  all_columns: Array<{
    key: string
    label: string
    type: string
    sortable: boolean
  }>
}

interface RankingData {
  代码: string
  [key: string]: any
}

interface StockInfo {
  item: string
  value: string
}

interface RankingTableProps {
  className?: string
}

const RankingTable: React.FC<RankingTableProps> = ({ className = "" }) => {
  const [factors, setFactors] = useState<Factor[]>([])
  const [allColumns, setAllColumns] = useState<Array<{ key: string, label: string, type: string, sortable: boolean }>>([])
  const [selectedFactors, setSelectedFactors] = useState<string[]>([])
  const [rankingData, setRankingData] = useState<RankingData[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [days, setDays] = useState(100)
  const [sortColumn, setSortColumn] = useState<string>('综合评分')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>('NVDA')
  const [stockInfo, setStockInfo] = useState<StockInfo[]>([])
  const [stockInfoLoading, setStockInfoLoading] = useState(false)
  const [stockInfoError, setStockInfoError] = useState<string | null>(null)
  const chartContainerRef = useRef<HTMLDivElement | null>(null)
  const tradingViewContainerId = useMemo(
    () => `tradingview-widget-${Math.random().toString(36).slice(2)}`,
    []
  )

  // Fetch available factors on component mount
  useEffect(() => {
    fetchFactors()
    // Fetch default stock info
    if (selectedSymbol) {
      fetchStockInfo(selectedSymbol)
    }
  }, [])

  // Auto-fetch ranking data when factors are selected
  useEffect(() => {
    if (selectedFactors.length > 0) {
      fetchRankingData()
    }
  }, [selectedFactors, days])

  // Initialize TradingView chart
  useTradingViewChart(chartContainerRef, tradingViewContainerId, selectedSymbol)

  const fetchFactors = async () => {
    try {
      const response = await fetch('/api/ranking/factors')
      const data: FactorsResponse = await response.json()

      if (data.success) {
        setFactors(data.factors)
        setAllColumns(data.all_columns || [])
        // Auto-select all factors by default
        const factorIds = data.factors.map((f: Factor) => f.id)
        setSelectedFactors(factorIds)
      } else {
        setError('Failed to fetch factors')
      }
    } catch (err) {
      setError('Failed to connect to server')
      console.error('Error fetching factors:', err)
    }
  }

  const fetchRankingData = async () => {
    if (selectedFactors.length === 0) return

    setLoading(true)
    setError(null)

    try {
      const factorsParam = selectedFactors.join(',')
      const response = await fetch(`/api/ranking/table?days=${days}&factors=${factorsParam}&limit=50`)
      const data = await response.json()

      if (data.success) {
        setRankingData(data.data || [])

        // Auto-sort by 综合评分 if available, otherwise first numeric column
        if (data.data && data.data.length > 0) {
          const firstRow = data.data[0]
          if ('综合评分' in firstRow && !sortColumn) {
            setSortColumn('综合评分')
          } else if (!sortColumn) {
            const numericColumns = Object.keys(firstRow).filter(key =>
              key !== '代码' && typeof firstRow[key] === 'number'
            )
            if (numericColumns.length > 0) {
              setSortColumn(numericColumns[0])
            }
          }
        }
      } else {
        setError(data.message || 'Failed to fetch ranking data')
      }
    } catch (err) {
      setError('Failed to connect to server')
      console.error('Error fetching ranking data:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortColumn(column)
      setSortDirection('desc')
    }
  }

  const fetchStockInfo = async (symbol: string) => {
    if (!symbol) return

    setStockInfoLoading(true)
    setStockInfoError(null)

    try {
      const response = await fetch(`/api/ranking/stock-info/${symbol}`)
      const data = await response.json()
      
      if (data.success) {
        setStockInfo(data.data || [])
      } else {
        setStockInfoError(data.error || 'Failed to fetch stock info')
        setStockInfo([])
      }
    } catch (err) {
      setStockInfoError('Failed to connect to server')
      setStockInfo([])
      console.error('Error fetching stock info:', err)
    } finally {
      setStockInfoLoading(false)
    }
  }

  const handleSelectSymbol = (code: string) => {
    const normalizedSymbol = normalizeSymbol(code)
    setSelectedSymbol(normalizedSymbol)
    fetchStockInfo(code) // Use original code for API call
  }

  const getSortedData = () => {
    if (!sortColumn || rankingData.length === 0) return rankingData

    return [...rankingData].sort((a, b) => {
      const aVal = a[sortColumn]
      const bVal = b[sortColumn]

      // Handle null/undefined values
      if (aVal == null && bVal == null) return 0
      if (aVal == null) return 1
      if (bVal == null) return -1

      // Numeric comparison
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal
      }

      // String comparison
      const aStr = String(aVal)
      const bStr = String(bVal)
      return sortDirection === 'asc'
        ? aStr.localeCompare(bStr)
        : bStr.localeCompare(aStr)
    })
  }

  const formatValue = (value: any, type?: string) => {
    if (value == null) return '-'

    if (typeof value === 'number') {
      if (type === 'score') {
        return (value * 100).toFixed(1) + '%'
      }
      return value.toFixed(4)
    }

    return String(value)
  }

  const getColumns = () => {
    if (rankingData.length === 0) return ['代码']

    const allColumns = Object.keys(rankingData[0])
    // Move 代码 to the front
    return ['代码', ...allColumns.filter(col => col !== '代码')]
  }

  const getColumnLabel = (column: string) => {
    // First check in allColumns (includes composite score)
    const col = allColumns.find(c => c.key === column)
    if (col) return col.label

    // Fallback to factor columns
    for (const factor of factors) {
      const factorCol = factor.columns.find(c => c.key === column)
      if (factorCol) return factorCol.label
    }
    return column
  }

  const getColumnType = (column: string) => {
    // First check in allColumns (includes composite score)
    const col = allColumns.find(c => c.key === column)
    if (col) return col.type

    // Fallback to factor columns
    for (const factor of factors) {
      const factorCol = factor.columns.find(c => c.key === column)
      if (factorCol) return factorCol.type
    }
    return 'text'
  }

  const getSortIcon = (column: string) => {
    if (sortColumn !== column) return null
    return sortDirection === 'asc' ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />
  }

  return (
    <div className={`flex h-full ${className}`}>
      <div className="flex-1 pr-4">

        {/* Controls */}
        <div className="flex gap-4 mb-4 flex-wrap">
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium">历史天数:</label>
            <Select value={days.toString()} onValueChange={(value) => setDays(parseInt(value))}>
              <SelectTrigger className="w-24">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="30">30天</SelectItem>
                <SelectItem value="60">60天</SelectItem>
                <SelectItem value="100">100天</SelectItem>
                <SelectItem value="200">200天</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-sm font-medium">因子:</label>
            <Select
              value={selectedFactors.length === factors.length ? "all" : "custom"}
              onValueChange={(value) => {
                if (value === "all") {
                  setSelectedFactors(factors.map(f => f.id))
                } else if (value === "momentum") {
                  setSelectedFactors(["momentum"])
                } else if (value === "support") {
                  setSelectedFactors(["support"])
                }
              }}
            >
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部因子</SelectItem>
                <SelectItem value="momentum">动量因子</SelectItem>
                <SelectItem value="support">支撑因子</SelectItem>
              </SelectContent>
            </Select>
          </div>
                      <Button
              onClick={fetchRankingData}
              disabled={loading || selectedFactors.length === 0}
              size="sm"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
        </div>

        {/* Error message */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="w-6 h-6 animate-spin mr-2" />
            <span>正在计算因子排行...</span>
          </div>
        )}

        {/* Table */}
        {!loading && rankingData.length > 0 && (
          <div className="border rounded-md">
            <Table>
              <TableHeader>
                <TableRow>
                  {getColumns().map((column) => (
                    <TableHead
                      key={column}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => handleSort(column)}
                    >
                      <div className="flex items-center gap-1">
                        {getColumnLabel(column)}
                        {getSortIcon(column)}
                      </div>
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {getSortedData().map((row, index) => (
                  <TableRow key={row.代码 || index}>
                    {getColumns().map((column) => (
                      <TableCell key={column}>
                        {column === '代码' ? (
                          <button
                            onClick={() => handleSelectSymbol(row[column])}
                            className="font-mono font-bold hover:text-blue-800 hover:underline cursor-pointer"
                          >
                            {row[column]}
                          </button>
                        ) : (
                          formatValue(row[column], getColumnType(column))
                        )}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && rankingData.length === 0 && selectedFactors.length > 0 && (
          <div className="text-center py-8 text-muted-foreground">
            <TrendingUp className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>暂无排行数据</p>
            <p className="text-sm">请检查数据库中是否有足够的K线数据</p>
          </div>
        )}

        {/* No factors selected */}
        {selectedFactors.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            <p>请选择要计算的因子</p>
          </div>
        )}
      </div>

      <div className="flex-1 border-l pl-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-medium">
            {selectedSymbol ? `${selectedSymbol} - Stock Chart` : 'Select a stock'}
          </h2>
          <div className="text-sm text-muted-foreground">click on a stock code to view chart</div>
        </div>
        <div className="relative w-full h-[50vh] mb-4">
          <div
            ref={chartContainerRef}
            id={tradingViewContainerId}
            className="h-full w-full"
          />
        </div>

        {/* Stock Info Section */}
        <div className="border-t pt-4">
          
          {stockInfoLoading && (
            <div className="flex items-center justify-center py-4">
              <RefreshCw className="w-4 h-4 animate-spin mr-2" />
              <span className="text-sm">Loading stock info...</span>
            </div>
          )}

          {stockInfoError && (
            <div className="text-red-700">
              {stockInfoError}
            </div>
          )}

          {!stockInfoLoading && !stockInfoError && stockInfo.length > 0 && (
            <div className="max-h-[35vh] overflow-y-auto">
              <div className="grid grid-cols-1 gap-1 text-sm">
                {stockInfo.map((info, index) => (
                  <div key={index} className="flex justify-between py-1 border-b border-gray-500 last:border-b-0">
                    <span className="font-medium text-gray-600 truncate mr-2">{info.item}:</span>
                    <span >{info.value || '-'}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {!stockInfoLoading && !stockInfoError && stockInfo.length === 0 && selectedSymbol && (
            <div className="text-center py-4 text-gray-500 text-sm">
              No information available for {selectedSymbol}
            </div>
          )}

          {!selectedSymbol && (
            <div className="text-center py-4 text-gray-500 text-sm">
              Select a stock to view information
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function useTradingViewChart(
  containerRef: React.RefObject<HTMLDivElement | null>,
  containerId: string,
  symbol: string | null
) {
  const [theme, setTheme] = useState<'light' | 'dark'>('dark')

  useEffect(() => {
    if (typeof document === 'undefined') {
      setTheme('dark')
      return
    }

    const updateTheme = () => {
      setTheme(document.documentElement.classList.contains('dark') ? 'dark' : 'light')
    }

    // 初始设置
    updateTheme()

    // 监听主题变化
    const observer = new MutationObserver(updateTheme)
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    })

    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    if (!symbol) {
      clearContainerChildren(container)
      return
    }

    const normalizedSymbol = normalizeSymbol(symbol)
    const widgetContainerId = containerId
    container.id = widgetContainerId
    clearContainerChildren(container)

    let widgetScript: HTMLScriptElement | null = null
    let pollTimer: number | null = null
    const initializeWidget = () => {
      const TradingView = window.TradingView
      if (!TradingView || typeof TradingView.widget !== 'function') {
        console.error('TradingView widget unavailable')
        return
      }

      new TradingView.widget({
        autosize: true,
        symbol: normalizedSymbol,
        interval: 'D',
        timezone: 'America/New_York',
        theme,
        style: '1',
        locale: 'en',
        toolbar_bg: '#f1f3f6',
        hide_legend: false,
        hide_top_toolbar: false,
        allow_symbol_change: false,
        withdateranges: true,
        container_id: widgetContainerId,
        studies: [
          {
            "id": "MASimple@tv-basicstudies",
            "inputs": {
              "length": 5
            }
          },
          {
            "id": "MASimple@tv-basicstudies",
            "inputs": {
              "length": 20
            }
          }
        ]
      })
    }

    if (window.TradingView && typeof window.TradingView.widget === 'function') {
      initializeWidget()
    } else if (!window.__tradingViewScriptLoading) {
      window.__tradingViewScriptLoading = true
      widgetScript = document.createElement('script')
      widgetScript.src = 'https://s3.tradingview.com/tv.js'
      widgetScript.async = true
      widgetScript.onload = () => {
        window.__tradingViewScriptLoading = false
        initializeWidget()
      }
      widgetScript.onerror = () => console.error('Failed to load TradingView script')
      document.body.appendChild(widgetScript)
    } else {
      pollTimer = window.setInterval(() => {
        if (window.TradingView && typeof window.TradingView.widget === 'function') {
          window.clearInterval(pollTimer as number)
          initializeWidget()
        }
      }, 100)
    }

    return () => {
      if (widgetScript) {
        widgetScript.onload = null
      }
      if (pollTimer !== null) {
        window.clearInterval(pollTimer)
      }
      clearContainerChildren(container)
    }
  }, [containerRef, containerId, symbol, theme])
}

function normalizeSymbol(symbol: string): string {
  return symbol.replace(/\.US$/i, '').trim().toUpperCase()
}

function clearContainerChildren(container: HTMLElement) {
  while (container.firstChild) {
    container.removeChild(container.firstChild)
  }
}

export default RankingTable