import React, { useState, useEffect } from 'react'
import { PieChart, ArrowLeftRight, Settings } from 'lucide-react'
import SettingsDialog from './SettingsDialog'
import { checkRequiredConfigs } from '@/lib/api'

export default function Sidebar() {
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
    if (!open && showRequiredConfig) {
      // 重新检查配置是否完整
      checkConfigs().then(() => {
        // 如果配置完整了，关闭必需配置对话框
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
      })
    }
  }

  return (
    <>
      <aside className="w-16 border-r h-full p-2 flex flex-col items-center">
        <nav className="space-y-4">
          <a 
            className="flex items-center justify-center w-10 h-10 rounded-lg hover:bg-gray-100 transition-colors" 
            href="#portfolio"
            title="Portfolio"
          >
            <PieChart className="w-5 h-5 text-gray-600" />
          </a>
          <a 
            className="flex items-center justify-center w-10 h-10 rounded-lg hover:bg-gray-100 transition-colors" 
            href="#trading"
            title="Trading"
          >
            <ArrowLeftRight className="w-5 h-5 text-gray-600" />
          </a>
          <button
            className="flex items-center justify-center w-10 h-10 rounded-lg hover:bg-gray-100 transition-colors"
            onClick={() => setSettingsOpen(true)}
            title="Settings"
          >
            <Settings className="w-5 h-5 text-gray-600" />
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
        onOpenChange={() => {}} 
        isRequired={true}
      />
    </>
  )
}
