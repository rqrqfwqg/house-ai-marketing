/**
 * 文案 API
 */
import client from './client'
import type {
  Script,
  ScriptGenerateRequest,
  ScriptUpdateRequest,
  ScriptListResponse,
} from '@/types'

/**
 * AI 生成文案
 */
export async function generateScript(
  req: ScriptGenerateRequest
): Promise<Script> {
  const { data } = await client.post('/scripts/generate', req)
  return data
}

/**
 * 获取文案列表
 */
export async function getScripts(
  houseId?: number,
  skip: number = 0,
  limit: number = 100
): Promise<ScriptListResponse> {
  const { data } = await client.get('/scripts', {
    params: { house_id: houseId, skip, limit },
  })
  return data
}

/**
 * 获取文案详情
 */
export async function getScript(id: number): Promise<Script> {
  const { data } = await client.get(`/scripts/${id}`)
  return data
}

/**
 * 更新文案
 */
export async function updateScript(
  id: number,
  req: ScriptUpdateRequest
): Promise<Script> {
  const { data } = await client.put(`/scripts/${id}`, req)
  return data
}
