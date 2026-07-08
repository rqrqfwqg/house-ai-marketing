/**
 * 公众号账号管理 API
 */
import client from './client'
import type {
  WechatAccount,
  WechatAccountCreate,
  WechatAccountUpdate,
  WechatAccountListResponse,
  WechatTestResponse,
} from '@/types'

/**
 * 获取公众号账号列表
 * @param activeOnly 仅返回启用账号（发布下拉用）
 */
export async function getWechatAccounts(
  activeOnly?: boolean
): Promise<WechatAccountListResponse> {
  const { data } = await client.get('/wechat-accounts', {
    params: activeOnly === undefined ? {} : { active_only: activeOnly },
  })
  return data
}

/**
 * 新增公众号账号
 */
export async function createWechatAccount(
  req: WechatAccountCreate
): Promise<WechatAccount> {
  const { data } = await client.post('/wechat-accounts', req)
  return data
}

/**
 * 编辑公众号账号
 */
export async function updateWechatAccount(
  id: number,
  req: WechatAccountUpdate
): Promise<WechatAccount> {
  const { data } = await client.put(`/wechat-accounts/${id}`, req)
  return data
}

/**
 * 删除公众号账号
 */
export async function deleteWechatAccount(
  id: number
): Promise<{ success: boolean; message: string }> {
  const { data } = await client.delete(`/wechat-accounts/${id}`)
  return data
}

/**
 * 测试账号连通性（用解密后的凭证拉取 access_token 验证）
 */
export async function testWechatAccount(
  id: number
): Promise<WechatTestResponse> {
  const { data } = await client.post(`/wechat-accounts/${id}/test`)
  return data
}
