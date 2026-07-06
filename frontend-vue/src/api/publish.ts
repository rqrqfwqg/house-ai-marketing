/**
 * 发布 API
 */
import client from './client'
import type {
  Platform,
  PublishRequest,
  PublishResponse,
  PublishLog,
  XhsQrCodeResponse,
  XhsLoginStatusResponse,
} from '@/types'

/**
 * 发布到小红书
 */
export async function publishToXiaohongshu(
  req: PublishRequest
): Promise<PublishResponse> {
  const { data } = await client.post('/publish/xiaohongshu', req)
  return data
}

/**
 * 创建微信草稿
 */
export async function publishToWechat(
  req: PublishRequest
): Promise<PublishResponse> {
  const { data } = await client.post('/publish/wechat', req)
  return data
}

/**
 * 发布（通用入口）
 */
export async function publish(
  platform: Platform,
  req: PublishRequest
): Promise<PublishResponse> {
  if (platform === 'xiaohongshu') {
    return publishToXiaohongshu(req)
  } else {
    return publishToWechat(req)
  }
}

/**
 * 获取发布记录
 */
export async function getPublishLogs(
  houseId?: number
): Promise<PublishLog[]> {
  const { data } = await client.get('/publish/logs', {
    params: { house_id: houseId },
  })
  return data
}

/**
 * 获取小红书登录二维码
 */
export async function getXhsQrCode(): Promise<XhsQrCodeResponse> {
  const { data } = await client.get('/publish/xhs-qrcode')
  return data
}

/**
 * 查询小红书登录状态
 */
export async function getXhsLoginStatus(): Promise<XhsLoginStatusResponse> {
  const { data } = await client.get('/publish/xhs-login-status')
  return data
}
