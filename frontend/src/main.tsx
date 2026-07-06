/*
 * React 应用入口文件
 * 负责：挂载根组件、导入全局样式、初始化Vant UI
 */
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'  // 导入全局样式（包含Tailwind指令）

// 获取根元素
const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
)

// 渲染应用
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
