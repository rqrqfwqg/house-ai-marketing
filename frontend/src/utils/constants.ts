/*
 * 常量定义
 * 定义：平台列表、模板风格、API地址等
 */

/**
 * 后端API基础地址
 */
export const API_BASE_URL = 'http://localhost:8899/api/v1';

/**
 * 前端开发服务器地址
 */
export const FRONTEND_URL = 'http://localhost:3000';

/**
 * 模板风格配置
 */
export const TEMPLATE_STYLES = {
  professional: {
    label: '专业商务',
    description: '严谨专业，突出房屋品质和性价比',
    icon: '💼',
  },
  friendly: {
    label: '亲切友好',
    description: '温暖亲切，营造家的感觉',
    icon: '😊',
  },
  urgent: {
    label: '紧迫促销',
    description: '制造紧迫感，促进快速决策',
    icon: '🔥',
  },
} as const;

/**
 * 发布平台配置
 */
export const PLATFORMS = {
  xiaohongshu: {
    label: '小红书',
    description: '发布笔记到小红书',
    icon: '📕',
    color: 'red',
  },
  wechat: {
    label: '微信公众号',
    description: '创建公众号草稿',
    icon: '💬',
    color: 'green',
  },
} as const;

/**
 * 文件上传配置
 */
export const UPLOAD_CONFIG = {
  maxImages: 10,
  maxImageSize: 10 * 1024 * 1024, // 10MB
  allowedTypes: ['image/jpeg', 'image/png', 'image/webp'],
  allowedExtensions: ['.jpg', '.jpeg', '.png', '.webp'],
} as const;

/**
 * 文案生成配置
 */
export const SCRIPT_CONFIG = {
  maxTokens: 2000,
  temperature: 0.7,
  maxTitleLength: 20,
  maxBodyLength: 500,
} as const;

/**
 * 分页配置
 */
export const PAGINATION = {
  defaultPageSize: 20,
  pageSizeOptions: [10, 20, 50, 100],
} as const;

/**
 * 错误码映射
 */
export const ERROR_MESSAGES = {
  400: '请求参数错误',
  401: '未授权，请重新登录',
  403: '拒绝访问',
  404: '请求的资源不存在',
  500: '服务器内部错误',
  503: '服务暂不可用',
} as const;

/**
 * 成功消息
 */
export const SUCCESS_MESSAGES = {
  upload: '上传成功！',
  generate: '文案生成成功！',
  save: '保存成功！',
  publish: '发布成功！',
  delete: '删除成功！',
} as const;
