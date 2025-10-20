import React, { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { getXueqiuCookie, saveXueqiuCookie } from '@/lib/api'

interface SettingsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function SettingsDialog({ open, onOpenChange }: SettingsDialogProps) {
  const [cookieValue, setCookieValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (open) {
      loadCurrentCookie()
    }
  }, [open])

  const loadCurrentCookie = async () => {
    try {
      const data = await getXueqiuCookie()
      if (data.has_cookie && data.value) {
        setCookieValue(data.value)
      }
    } catch (err) {
      console.error('Failed to load cookie:', err)
      // 如果无法加载现有配置，继续允许用户输入新配置
    }
  }

  const handleSave = async () => {
    setLoading(true)
    setError('')

    try {
      const trimmed = cookieValue.trim()
      if (!trimmed) {
        onOpenChange(false)
        setError('')
        setLoading(false)
        return
      }

      const data = await saveXueqiuCookie(trimmed)
      
      if (data.success) {
        onOpenChange(false)
        setCookieValue('')
        setError('')
      } else {
        setError(data.message || '保存失败，请重试')
      }
    } catch (err: any) {
      console.error('Save error:', err)
      
      // 提供更详细的错误信息
      if (err.message.includes('HTTP error! status: 400')) {
        setError('Cookie格式无效，请检查Cookie字符串格式')
      } else if (err.message.includes('HTTP error! status: 500')) {
        setError('服务器内部错误，请稍后重试')
      } else if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
        setError('网络连接失败，请检查网络连接')
      } else if (err.message.includes('Response is not JSON')) {
        setError('服务器响应格式错误，请联系管理员')
      } else {
        setError(`保存失败: ${err.message || '未知错误'}`)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = () => {
    setCookieValue('')
    setError('')
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>雪球Cookie配置</DialogTitle>
          <DialogDescription>
            更新雪球Cookie配置以确保市场数据正常获取（可选）。
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <label htmlFor="cookie" className="text-sm font-medium">
              Cookie字符串 *
            </label>
            <textarea
              id="cookie"
              value={cookieValue}
              onChange={(e) => {
                setCookieValue(e.target.value)
                setError('')
              }}
              placeholder="请粘贴从浏览器开发者工具中复制的雪球Cookie字符串..."
              className="min-h-[100px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
            <p className="text-xs text-muted-foreground">
              如何获取: 1. 访问 xueqiu.com 并登录 2. 按F12打开开发者工具 3. 在Network标签页中找到任意API请求 4. 复制请求头中的完整Cookie值
            </p>
          </div>
          
          {error && (
            <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
              {error}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleCancel}>
            取消
          </Button>
          <Button onClick={handleSave} disabled={loading}>
            {loading ? '保存中...' : '保存'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}