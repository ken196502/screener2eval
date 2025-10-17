import React, { useState, useEffect } from 'react'
import { PieChart, Settings, TrendingUp, Newspaper } from 'lucide-react'
import SettingsDialog from './SettingsDialog'
import { checkRequiredConfigs } from '@/lib/api'

interface SidebarProps {
  currentPage?: string
  onPageChange?: (page: string) => void
}

export default function Sidebar({ currentPage = 'portfolio', onPageChange }: SidebarProps) {
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [showRequiredConfig, setShowRequiredConfig] = useState(false)

  useEffect(() => {
    checkConfigs()
  }, [])

  const checkConfigs = async () => {
    try {
      const data = await checkRequiredConfigs()
      if (!data.has_required_configs) {
        setShowRequiredConfig(true)
      }
    } catch (err) {
      console.error('Failed to check required configs:', err)
      // 如果无法连接到后端，先不显示必需配置对话框
      // 用户可以手动通过设置按钮进行配置
    }
  }

  const handleSettingsClose = (open: boolean) => {
    setSettingsOpen(open)
    if (!open) {
      // 重新检查配置是否完整
      checkConfigs().then(async () => {
        try {
          const data = await checkRequiredConfigs()
          if (data.has_required_configs) {
            setShowRequiredConfig(false)
          }
        } catch (err) {
          console.error('Error checking configs after save:', err)
        }
      })
    }
  }

  const handleRequiredConfigClose = (open: boolean) => {
    if (!open) {
      // 重新检查配置是否完整
      checkConfigs().then(async () => {
        try {
          const data = await checkRequiredConfigs()
          if (data.has_required_configs) {
            setShowRequiredConfig(false)
          }
        } catch (err) {
          console.error('Error checking configs after save:', err)
        }
      })
    }
  }

  return (
    <>
      <aside className="w-16 border-r h-full p-2 flex flex-col items-center">
        <nav className="space-y-4">
           <button 
            className={`flex items-center justify-center w-10 h-10 rounded-lg transition-colors ${
              currentPage === 'news' 
                ? 'bg-secondary/80 text-secondary-foreground' 
                : 'hover:bg-muted text-muted-foreground'
            }`}
            onClick={() => onPageChange?.('news')}
            title="US Stock Movement"
          >
            <Newspaper className="w-5 h-5" />
          </button>

          <button 
            className={`flex items-center justify-center w-10 h-10 rounded-lg transition-colors ${
              currentPage === 'portfolio' 
                ? 'bg-secondary/80 text-secondary-foreground' 
                : 'hover:bg-muted text-muted-foreground'
            }`}
            onClick={() => onPageChange?.('portfolio')}
            title="Portfolio"
          >
            <PieChart className="w-5 h-5" />
          </button>

          <button 
            className={`flex items-center justify-center w-10 h-10 rounded-lg transition-colors ${
              currentPage === 'asset-curve' 
                ? 'bg-secondary/80 text-secondary-foreground' 
                : 'hover:bg-muted text-muted-foreground'
            }`}
            onClick={() => onPageChange?.('asset-curve')}
            title="Asset Curve"
          >
            <TrendingUp className="w-5 h-5" />
          </button>

          <button
            className="flex items-center justify-center w-10 h-10 rounded-lg hover:bg-muted transition-colors text-muted-foreground"
            onClick={() => setSettingsOpen(true)}
            title="Settings"
          >
            <Settings className="w-5 h-5" />
          </button>
        </nav>
      </aside>

      {/* Settings Dialog */}
      <SettingsDialog 
        open={settingsOpen} 
        onOpenChange={handleSettingsClose}
      />

      {/* Required Config Dialog */}
      <SettingsDialog 
        open={showRequiredConfig} 
        onOpenChange={handleRequiredConfigClose} 
        isRequired={true}
      />
    </>
  )
}
