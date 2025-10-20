import React, { useState, useEffect, useMemo } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ExternalLink } from 'lucide-react'
import StockViewer from '@/components/common/StockViewer'
import StockViewerDrawer from '@/components/common/StockViewerDrawer'

interface NewsItem {
  content_id?: string
  title: string
  digest: string
  keywords?: string
  author: string
  create_time: string
  browse_count?: string
  url?: string
  image?: string
  stock_codes?: string[]
  content?: string
}

interface NewsResponse {
  status: string
  data: NewsItem[]
  page: number
  total: number
}

export default function NewsPanel() {
  const [gmteightNews, setGmteightNews] = useState<NewsItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>('IXIC')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)

  // Detect mobile device
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768)
    }
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  const fetchGmteightNews = async (page: number = 1) => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch(`/api/news/gmteight?page=${page}&save_kline=true`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data: NewsResponse = await response.json()

      if (data.status === 'success') {
        setGmteightNews(data.data)
      } else {
        throw new Error('获取新闻失败')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取GMT Eight新闻失败')
      console.error('Error fetching GMT Eight news:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchGmteightNews(currentPage)
  }, [currentPage])



  const handleRefresh = () => {
    fetchGmteightNews(currentPage)
  }

  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage)
  }

  const normalizeSymbol = (symbol: string): string => {
    return symbol.replace(/\.US$/i, '').trim().toUpperCase()
  }

  const handleSelectSymbol = (code: string) => {
    const normalizedSymbol = normalizeSymbol(code)
    setSelectedSymbol(normalizedSymbol)
    if (isMobile) {
      setDrawerOpen(true)
    }
  }

  const allStockCodes = useMemo(() => {
    const codes: string[] = []
    gmteightNews.forEach(news => {
      if (news.stock_codes) {
        news.stock_codes.forEach(code => {
          const normalized = normalizeSymbol(code)
          if (!codes.includes(normalized)) {
            codes.push(normalized)
          }
        })
      }
    })
    return codes
  }, [gmteightNews])

  const handleDrawerNavigate = (direction: 'prev' | 'next') => {
    if (allStockCodes.length === 0 || !selectedSymbol) return
    const currentIndex = allStockCodes.indexOf(selectedSymbol)
    if (currentIndex === -1) return
    
    let newIndex = currentIndex
    if (direction === 'prev' && currentIndex > 0) {
      newIndex = currentIndex - 1
    } else if (direction === 'next' && currentIndex < allStockCodes.length - 1) {
      newIndex = currentIndex + 1
    }
    
    if (newIndex !== currentIndex) {
      setSelectedSymbol(allStockCodes[newIndex])
    }
  }

  const NewsRow = ({ news, index }: { news: NewsItem; index: number }) => (
    <div className="p-2 hover:bg-muted border-b border-border">
      <div className="flex gap-3">
        <div className="w-4 text-sm text-muted-foreground flex-shrink-0 text-center">
          {index + 1}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-foreground line-clamp-2">{news.digest}</p>
          <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center space-x-2">
              <span>{news.create_time}</span>
              {news.url ? (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => window.open(news.url as string, '_blank')}
                  className="p-1 h-6 w-6"
                >
                  <ExternalLink className="w-3 h-3" />
                </Button>
              ) : null}
            </div>
            {news.stock_codes && news.stock_codes.length > 0 ? (
              <div className="flex flex-wrap justify-end gap-1">
                {news.stock_codes.map((code, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSelectSymbol(code)}
                    className="px-2 py-1 bg-secondary text-secondary-foreground text-xs rounded font-medium"
                  >
                    {code}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  )

  if (error) {
    return (
      <div className="p-2">
        <Card className="p-2 text-center">
          <div className="text-red-600 mb-4">
            <h3 className="text-lg font-semibold mb-2">获取新闻失败</h3>
            <p className="text-sm">{error}</p>
          </div>
          <Button onClick={handleRefresh} variant="outline">
            重试
          </Button>
        </Card>
      </div>
    )
  }

  return (
    <div className="p-2">
      <div className="grid grid-cols-3 gap-2">
        <div className="col-span-1">
          {loading ? (
            <div className="text-center py-8">
              <div className="inline-block animate-spin rounded-full h-8 w-4 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-muted-foreground">Fetching...</p>
            </div>
          ) : gmteightNews.length > 0 ? (
            <div>
              <div className="bg-card border border-border rounded-lg overflow-hidden">
                <div className="max-h-[calc(100vh-8rem)] overflow-y-auto">
                  {gmteightNews.map((news, index) => (
                    <NewsRow
                      key={news.content_id || `${news.title}-${index}`}
                      news={news}
                      index={index}
                    />
                  ))}
                </div>
              </div>

              <div className="flex justify-center space-x-2 mt-2">
                <Button onClick={handleRefresh} disabled={loading} variant="outline">
                  {loading ? 'Loading...' : 'Refresh'}
                </Button>
                <Button
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage <= 1}
                  variant="outline"
                  size="sm"
                >
                  Previous
                </Button>
                <span className="flex items-center px-3 text-sm text-muted-foreground">
                  Page {currentPage}
                </span>
                <Button
                  onClick={() => handlePageChange(currentPage + 1)}
                  variant="outline"
                  size="sm"
                >
                  Next
                </Button>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">No GMT Eight news</div>
          )}
        </div>

        {!isMobile && (
          <div className="col-span-2">
            <div className="bg-card border border-border rounded-lg p-4">
              <StockViewer
                symbol={selectedSymbol}
                title={selectedSymbol === 'IXIC' ? 'IXIC - NASDAQ Composite Index' : selectedSymbol ? `${selectedSymbol} - Stock Chart` : 'Select a stock'}
                subtitle="click on a stock to view the chart"
              />
            </div>
          </div>
        )}
      </div>

      {isMobile && (
        <StockViewerDrawer
          symbol={selectedSymbol}
          open={drawerOpen}
          onOpenChange={setDrawerOpen}
          stockList={allStockCodes}
          onNavigate={handleDrawerNavigate}
          title={selectedSymbol === 'IXIC' ? 'IXIC - NASDAQ Composite Index' : selectedSymbol || 'Stock Viewer'}
        />
      )}
    </div>
  )
}
