/*
 * 文案相关API调用
 * 封装：生成文案、获取详情、更新文案、获取列表
 */
import apiClient from './api';
import type { Script, ScriptGenerateRequest, ScriptUpdateRequest, ScriptListResponse } from '../types/script';

// 重新导出类型以便其他模块使用
export type { Script, ScriptGenerateRequest, ScriptUpdateRequest };

/**
 * 生成AI文案
 * @param request - 生成请求（house_id, template_style）
 * @returns 生成的文案
 */
export async function generateScript(
  request: ScriptGenerateRequest
): Promise<Script> {
  const response = await apiClient.post<Script>('/scripts/generate', request);
  return response.data;
}

/**
 * 获取文案详情
 * @param scriptId - 文案ID
 * @returns 文案详情
 */
export async function getScript(
  scriptId: number
): Promise<Script> {
  const response = await apiClient.get<Script>(`/scripts/${scriptId}`);
  return response.data;
}

/**
 * 更新文案（编辑后保存）
 * @param scriptId - 文案ID
 * @param request - 更新请求（title, body, tags）
 * @returns 更新后的文案
 */
export async function updateScript(
  scriptId: number,
  request: ScriptUpdateRequest
): Promise<Script> {
  const response = await apiClient.put<Script>(`/scripts/${scriptId}`, request);
  return response.data;
}

/**
 * 获取文案列表
 * @param params - 查询参数（house_id, skip, limit）
 * @returns 文案列表和总数
 */
export async function getScripts(params?: {
  house_id?: number;
  skip?: number;
  limit?: number;
}): Promise<ScriptListResponse> {
  const response = await apiClient.get<ScriptListResponse>('/scripts', {
    params,
  });
  
  return response.data;
}
