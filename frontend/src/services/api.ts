/*
 * API调用层（axios实例、拦截器、统一错误处理）
 * 负责：创建axios实例、请求/响应拦截器、统一错误处理
 */
import axios, { AxiosInstance, AxiosError } from 'axios';
import { ApiError } from '../types/api';

/**
 * 创建axios实例
 * 配置：baseURL、超时时间、请求/响应拦截器
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: '/api/v1',  // 通过vite代理转发到后端
  timeout: 30000,  // 30秒超时（AI生成可能需要较长时间）
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * 请求拦截器
 * 功能：添加token（如有）、打印请求日志
 */
apiClient.interceptors.request.use(
  (config) => {
    // 在请求发送前可以做些什么
    // 例如：从localStorage获取token并添加到请求头
    // const token = localStorage.getItem('token');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    
    console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, config.data);
    return config;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

/**
 * 响应拦截器
 * 功能：统一错误处理、token过期处理、打印响应日志
 */
apiClient.interceptors.response.use(
  (response) => {
    console.log(`[API Response] ${response.status} ${response.config.url}`, response.data);
    return response;
  },
  (error: AxiosError<ApiError>) => {
    // 统一错误处理
    if (error.response) {
      // 服务器返回了错误状态码
      const status = error.response.status;
      const detail = error.response.data?.detail || '未知错误';
      
      console.error(`[API Error] ${status} ${error.config?.url}`, detail);
      
      // 可以根据状态码做不同处理
      if (status === 401) {
        // token过期或未登录
        console.warn('登录已过期，请重新登录');
        // 可以在这里跳转到登录页
      } else if (status === 500) {
        // 服务器内部错误
        console.error('服务器内部错误，请稍后重试');
      }
    } else if (error.request) {
      // 请求已发送但没有收到响应（网络错误）
      console.error('[API Error] 网络错误，请检查网络连接');
    } else {
      // 请求配置出错
      console.error('[API Error] 请求配置错误', error.message);
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
