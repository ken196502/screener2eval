import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { RefreshCw, TrendingUp, TrendingDown } from 'lucide-react'
import StockViewer from '@/components/common/StockViewer'
import StockViewerDrawer from '@/components/common/StockViewerDrawer'

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
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)
  const tableContainerRef = useRef<HTMLDivElement | null>(null)
  const hasFocusedTableRef = useRef(false)

  // Detect mobile device
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768)
    }
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  // Fetch available factors on component mount
  useEffect(() => {
    fetchFactors()
  }, [])

  // Auto-fetch ranking data when factors are selected
  useEffect(() => {
    if (selectedFactors.length > 0) {
      fetchRankingData()
    }
  }, [selectedFactors, days])

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

  const normalizeSymbol = (symbol: string): string => {
    return symbol.replace(/\.US$/i, '').trim().toUpperCase()
  }

  const handleSelectSymbol = useCallback((code: string) => {
    const normalizedSymbol = normalizeSymbol(code)
    setSelectedSymbol(normalizedSymbol)
    if (isMobile) {
      setDrawerOpen(true)
    }
    tableContainerRef.current?.focus()
  }, [isMobile])

  const handleDrawerNavigate = (direction: 'prev' | 'next') => {
    if (sortedData.length === 0) return
    const normalizedSelection = selectedSymbol ? selectedSymbol : null
    const currentIndex = normalizedSelection
      ? sortedData.findIndex(row => normalizeSymbol(row.代码) === normalizedSelection)
      : -1
    
    let newIndex = currentIndex
    if (direction === 'prev' && currentIndex > 0) {
      newIndex = currentIndex - 1
    } else if (direction === 'next' && currentIndex < sortedData.length - 1) {
      newIndex = currentIndex + 1
    }
    
    if (newIndex !== currentIndex && newIndex >= 0) {
      handleSelectSymbol(sortedData[newIndex].代码)
    }
  }

  const sortedData = useMemo(() => {
    if (!sortColumn || rankingData.length === 0) return rankingData

    return [...rankingData].sort((a, b) => {
      const aVal = a[sortColumn]
      const bVal = b[sortColumn]

      if (aVal == null && bVal == null) return 0
      if (aVal == null) return 1
      if (bVal == null) return -1

      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal
      }

      const aStr = String(aVal)
      const bStr = String(bVal)
      return sortDirection === 'asc'
        ? aStr.localeCompare(bStr)
        : bStr.localeCompare(aStr)
    })
  }, [rankingData, sortColumn, sortDirection])

  useEffect(() => {
    const container = tableContainerRef.current
    if (!container || sortedData.length === 0) return

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return
      const normalizedSelection = selectedSymbol ? selectedSymbol : null
      const currentIndex = normalizedSelection
        ? sortedData.findIndex(row => normalizeSymbol(row.代码) === normalizedSelection)
        : -1

      const targetByIndex = (index: number) => {
        const normalizedIndex = Math.min(Math.max(index, 0), sortedData.length - 1)
        return sortedData[normalizedIndex]
      }

      if (event.key === 'ArrowDown') {
        event.preventDefault()
        const nextIndex = currentIndex >= 0 ? currentIndex + 1 : 0
        const target = targetByIndex(nextIndex)
        handleSelectSymbol(target.代码)
      } else if (event.key === 'ArrowUp') {
        event.preventDefault()
        if (currentIndex <= 0) return
        const nextIndex = currentIndex - 1
        const target = targetByIndex(nextIndex)
        handleSelectSymbol(target.代码)
      }
    }

    container.addEventListener('keydown', handleKeyDown)
    return () => container.removeEventListener('keydown', handleKeyDown)
  }, [handleSelectSymbol, selectedSymbol, sortedData])

  useEffect(() => {
    if (hasFocusedTableRef.current) return
    if (sortedData.length === 0) return
    tableContainerRef.current?.focus()
    hasFocusedTableRef.current = true
  }, [sortedData])

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

  const stockList = useMemo(() => sortedData.map(row => normalizeSymbol(row.代码)), [sortedData])

  return (
    <div className={`flex h-full ${className}`}>
      <div className={isMobile ? "w-full" : "flex-1 pr-4"}>

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
                <SelectItem value="all">All Factors</SelectItem>
                <SelectItem value="momentum">Momentum</SelectItem>
                <SelectItem value="support">Support</SelectItem>
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
            <span>Calculating...</span>
          </div>
        )}

        {/* Table */}
        {!loading && rankingData.length > 0 && (
          <div
            ref={tableContainerRef}
            className="border rounded-md h-[calc(100vh-12rem)] overflow-y-auto focus:outline-none"
            tabIndex={0}
          >
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
                {sortedData.map((row, index) => {
                  const isSelected = normalizeSymbol(row.代码) === selectedSymbol
                  return (
                    <TableRow
                      key={row.代码 || index}
                      className={`${isSelected ? 'bg-muted' : ''} cursor-pointer`}
                    >
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
                  )
                })}
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

      {!isMobile && (
        <div className="flex-1 border-l pl-4">
          <StockViewer 
            symbol={selectedSymbol}
            subtitle="click on a stock code to view chart"
          />
        </div>
      )}

      {isMobile && (
        <StockViewerDrawer
          symbol={selectedSymbol}
          open={drawerOpen}
          onOpenChange={setDrawerOpen}
          stockList={stockList}
          onNavigate={handleDrawerNavigate}
        />
      )}
    </div>
  )
}

function clearContainerChildren(container: HTMLElement) {
  while (container.firstChild) {
    container.removeChild(container.firstChild)
  }
}

export default RankingTable