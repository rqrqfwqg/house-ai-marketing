/*
 * 发布相关API调用
 * 封装：发布到小红书、创建公众号草稿、获取发布记录
 */
import apiClient from './api';
import type { PublishRequest, PublishResponse, PublishLog } from '../types/api';

// 重新导出类型以便其他模块使用
export type { PublishResponse };

/**
 * 发布文案到小红书
 * @param request - 发布请求（script_id, images）
 * @returns 发布结果
 */
export async function publishToXiaohongshu(
  request: PublishRequest
): Promise<PublishResponse> {
  const response = await apiClient.post<PublishResponse>('/publish/xiaohongshu', request);
  return response.data;
}

/**
 * 创建公众号草稿
 * @param request - 发布请求（script_id, images）
 * @returns 创建结果
 */
export async function createWechatDraft(
  request: PublishRequest
): Promise<PublishResponse> {
  const response = await apiClient.post<PublishResponse>('/publish/wechat', request);
  return response.data;
}

/**
 * 获取发布记录
 * @param houseId - 房源ID（可选）
 * @returns 发布记录列表
 */
export async function getPublishLogs(
  houseId?: number
): Promise<PublishLog[]> {
  const params = houseId ? { house_id: houseId } : {};
  const response = await apiClient.get<PublishLog[]>('/publish/logs', {
    params,
  });
  
  return response.data;
}
