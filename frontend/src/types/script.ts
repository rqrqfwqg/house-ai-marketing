/*
 * 文案相关类型定义
 * 定义：Script（文案）、ScriptGenerateRequest（生成请求）、ScriptResponse（响应）
 */

/**
 * 文案信息接口
 * 对应后端 ScriptResponse
 */
export interface Script {
  id: number;
  house_id: number;
  title: string;
  body: string;
  tags: string[];
  platform?: string;
  template_style?: string;
  created_at: string;  // ISO 8601 格式
}

/**
 * 文案生成请求接口
 * 对应后端 ScriptGenerateRequest
 */
export interface ScriptGenerateRequest {
  house_id: number;
  template_style?: 'professional' | 'friendly' | 'urgent';
}

/**
 * 文案更新请求接口
 * 对应后端 ScriptUpdateRequest
 */
export interface ScriptUpdateRequest {
  title?: string;
  body?: string;
  tags?: string[];
}

/**
 * 文案列表响应接口
 */
export interface ScriptListResponse {
  items: Script[];
  total: number;
}

/**
 * 模板风格枚举
 */
export type TemplateStyle = 'professional' | 'friendly' | 'urgent';

/**
 * 模板风格配置
 */
export const TEMPLATE_STYLES: Record<TemplateStyle, { label: string; description: string }> = {
  professional: {
    label: '专业商务',
    description: '严谨专业，突出房屋品质和性价比',
  },
  friendly: {
    label: '亲切友好',
    description: '温暖亲切，营造家的感觉',
  },
  urgent: {
    label: '紧迫促销',
    description: '制造紧迫感，促进快速决策',
  },
};
