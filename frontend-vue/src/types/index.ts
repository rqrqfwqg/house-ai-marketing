/**
 * TypeScript 类型定义
 * 房屋租赁 AI 营销系统
 */

// ==================== House ====================

export interface House {
  id: number
  title?: string
  address?: string
  rent?: number
  rooms?: string
  area?: number
  floor?: string
  tags: string[]
  highlights: string[]
  images: string[]
  created_at: string
  updated_at: string
}

export interface HouseCreate {
  title?: string
  address?: string
  rent?: number
  rooms?: string
  area?: number
  floor?: string
  tags?: string[]
  highlights?: string[]
}

export interface HouseListResponse {
  items: House[]
  total: number
}

export interface UploadResponse {
  id: number
  images: string[]
  message: string
}

// ==================== Script ====================

export type TemplateStyle = 'professional' | 'friendly' | 'urgent'

export interface Script {
  id: number
  house_id: number
  title: string
  body: string
  tags: string[]
  highlights: string[]
  platform?: string
  template_style?: string
  created_at: string
}

export interface ScriptGenerateRequest {
  house_id: number
  template_style?: TemplateStyle
  /** 目标发布平台（xiaohongshu / wechat），平台优先：生成即绑定，必填 */
  platform: Platform
}

export interface ScriptUpdateRequest {
  title?: string
  body?: string
  tags?: string[]
  highlights?: string[]
}

export interface ScriptListResponse {
  items: Script[]
  total: number
}

export const TEMPLATE_STYLES: Record<
  TemplateStyle,
  { label: string; description: string }
> = {
  professional: {
    label: '种草推荐',
    description: '博主真心推荐好窝，突出居住体验',
  },
  friendly: {
    label: '生活日记',
    description: '记录搬新家日常，温馨自然分享',
  },
  urgent: {
    label: '心动安利',
    description: '发现宝藏小屋，激动安利这个空间',
  },
}

// ==================== Publish ====================

export type Platform = 'xiaohongshu' | 'wechat'

export interface PublishRequest {
  script_id: number
  images: string[]
  wechat_account_id?: number
}

export interface PublishResponse {
  success: boolean
  platform: string
  note_id?: string
  media_id?: string
  content?: string
  editor_url?: string
  error?: string
}

export interface PublishLog {
  id: number
  house_id: number
  script_id: number
  platform: string
  status: 'pending' | 'success' | 'failed' | 'draft_created'
  error_msg?: string
  xhs_note_id?: string
  wechat_media_id?: string
  published_at?: string
  created_at: string
}

export interface XhsQrCodeResponse {
  success: boolean
  data: {
    qr_code?: string
    qr_code_url?: string
    expire_in?: number
    exprie_in?: number
  }
}

export interface XhsLoginStatusResponse {
  logged_in: boolean
}

// ==================== WeChat Account（公众号多账号） ====================

export interface WechatAccount {
  id: number
  name: string
  /** 脱敏后的 AppID（如 wx12********cdef），绝不返回明文 */
  app_id_masked: string
  remark?: string
  is_active: boolean
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface WechatAccountCreate {
  name: string
  app_id: string
  app_secret: string
  remark?: string
  is_active?: boolean
  is_default?: boolean
}

export interface WechatAccountUpdate {
  name?: string
  app_id?: string
  /** 留空表示不修改 */
  app_secret?: string
  remark?: string
  is_active?: boolean
  is_default?: boolean
}

export interface WechatAccountListResponse {
  items: WechatAccount[]
  total: number
}

export interface WechatTestResponse {
  success: boolean
  message: string
}

// ==================== Health ====================

export interface HealthResponse {
  status: string
  message: string
}
