/*
 * API响应通用类型定义
 * 定义：统一的错误格式、分页参数
 */

/**
 * API错误响应接口
 * 对应后端 ErrorResponse
 */
export interface ApiError {
  detail: string;
}

/**
 * API成功响应接口（通用）
 * 对应后端 SuccessResponse
 */
export interface ApiSuccess<T = unknown> {
  message: string;
  data?: T;
}

/**
 * 分页参数接口
 */
export interface PaginationParams {
  skip?: number;
  limit?: number;
}

/**
 * 发布平台枚举
 */
export type Platform = 'xiaohongshu' | 'wechat';

/**
 * 发布平台配置
 */
export const PLATFORMS: Record<Platform, { label: string; icon: string }> = {
  xiaohongshu: {
    label: '小红书',
    icon: '📕',
  },
  wechat: {
    label: '微信公众号',
    icon: '💬',
  },
};

/**
 * 发布请求接口
 * 对应后端 PublishRequest
 */
export interface PublishRequest {
  script_id: number;
  images: string[];
}

/**
 * 发布响应接口
 * 对应后端 PublishResponse
 */
export interface PublishResponse {
  success: boolean;
  platform: string;
  note_id?: string;  // 小红书笔记ID
  media_id?: string;  // 微信公众号素材ID
  error?: string;
}

/**
 * 发布记录接口
 * 对应后端 PublishLogResponse
 */
export interface PublishLog {
  id: number;
  house_id: number;
  script_id: number;
  platform: string;
  status: 'pending' | 'success' | 'failed' | 'draft_created';
  error_msg?: string;
  xhs_note_id?: string;
  wechat_media_id?: string;
  published_at?: string;
  created_at: string;
}
