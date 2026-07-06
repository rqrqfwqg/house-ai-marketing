/*
 * Vite 配置文件
 * 配置：开发服务器端口、代理（解决跨域问题）、构建选项
 */
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  
  // 开发服务器配置
  server: {
    port: 3000,  // 前端开发服务器端口（统一使用3000）
    host: '0.0.0.0',  // 允许外部访问
    proxy: {
      // 代理所有API请求到后端服务器
      '/api': {
        target: 'http://localhost:8901',  // 后端服务器地址
        changeOrigin: true,  // 修改请求头中的Origin
        rewrite: (path) => path,  // 保持路径不变（不剥离任何前缀）
      },
    },
  },
  
  // 构建配置
  build: {
    outDir: 'dist',  // 构建输出目录
    assetsDir: 'assets',  // 静态资源目录
    sourcemap: true,  // 生成source map（方便调试）
  },
  
  // 解析配置
  resolve: {
    alias: {
      '@': '/src',  // 路径别名（可选）
    },
  },
})
