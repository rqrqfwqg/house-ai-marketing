/*
 * 根组件
 * 负责：路由配置、全局布局、主题设置
 * 已移除 antd-mobile 依赖，使用纯 HTML + Tailwind
 */
import React from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'

// 页面组件
import UploadPage from './pages/UploadPage'
import GeneratePage from './pages/GeneratePage'
import PreviewPage from './pages/PreviewPage'
import PublishPage from './pages/PublishPage'
import HistoryPage from './pages/HistoryPage'

// 样式
import './index.css'

// 移动端布局组件
function MobileLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation()

  const getTitle = () => {
    if (location.pathname === '/upload') return '上传房源'
    if (location.pathname === '/generate') return '生成文案'
    if (location.pathname.startsWith('/preview')) return '预览文案'
    if (location.pathname === '/publish') return '发布管理'
    if (location.pathname === '/history') return '历史记录'
    return '房屋租赁AI营销系统'
  }

  return (
    <div className="mobile-container">
      {/* 顶部导航栏 */}
      <header className="app-header">
        <h1 className="app-title">{getTitle()}</h1>
        <span className="app-subtitle">AI营销</span>
      </header>

      {/* 主内容区 */}
      <main className="main-content">
        {children}
      </main>
    </div>
  )
}

const App: React.FC = () => {
  return (
    <BrowserRouter
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <MobileLayout>
        <Routes>
          <Route path="/" element={<Navigate to="/upload" replace />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/generate" element={<GeneratePage />} />
          <Route path="/preview/:id" element={<PreviewPage />} />
          <Route path="/publish" element={<PublishPage />} />
          <Route path="/history" element={<HistoryPage />} />
        </Routes>
      </MobileLayout>
    </BrowserRouter>
  )
}

export default App
