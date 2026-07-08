/**
 * Axios 实例 + 拦截器
 */
import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE || '/api/v1'

const client: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
client.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
client.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    // 统一错误处理由各调用方通过 ElMessage 展示
    if (error.response) {
      const status = error.response.status
      const msg =
        error.response.data?.detail ||
        error.response.data?.message ||
        `请求失败 (${status})`
      console.error(`[API Error] ${status}: ${msg}`)
    } else if (error.request) {
      console.error('[API Error] 网络请求无响应')
    } else {
      console.error(`[API Error] ${error.message}`)
    }
    return Promise.reject(error)
  }
)

export default client
