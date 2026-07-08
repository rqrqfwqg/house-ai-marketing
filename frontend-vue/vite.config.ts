import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    // 生产构建走子路径 /house-ai/（由 .env.production 的 VITE_BASE 控制）；开发默认 '/'
    base: env.VITE_BASE || '/',
    plugins: [vue()],
    server: {
      port: 3001,
      host: '0.0.0.0',
      proxy: {
        // 开发期后端在 8902；生产由 nginx 反代，不走这里
        '/api': {
          target: 'http://localhost:8902',
          changeOrigin: true,
        },
        '/uploads': {
          target: 'http://localhost:8902',
          changeOrigin: true,
        },
        // 生产命名空间下的上传路径（对应后端 /house-ai/uploads）
        '/house-ai/uploads': {
          target: 'http://localhost:8902',
          changeOrigin: true,
        },
      },
    },
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
  }
})
