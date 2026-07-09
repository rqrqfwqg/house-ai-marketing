/**
 * 平台约束镜像（前端唯一真源，与后端 backend/services/platform_rules.py 保持一致）
 *
 * 设计约束（来自增量架构设计「共享知识」）：
 * 1. 平台枚举值必须与后端 / 数据库 / 路由一致：'xiaohongshu' | 'wechat'。禁止新别名。
 * 2. 计量口径：
 *    - 微信标题：UTF-8 **字节**（TextEncoder 编码后长度），上限 64（纯中文≈21字）。
 *    - 小红书标题/正文/话题：**字符**（String.length），上限 20 / 1000 / 10。
 * 3. 本文件为约束镜像，逻辑（countTitle / countBody）与后端完全对齐，
 *    前后端以同一套常量与算法工作，避免漂移。
 *
 * 注意：本文件仅用浏览器原生 API（TextEncoder、String.length），不引入任何第三方依赖。
 */

export type Platform = 'xiaohongshu' | 'wechat'

export type TitleUnit = 'byte' | 'char'

export interface PlatformRule {
  /** 标题上限数值 */
  titleMax: number
  /** 标题计量口径：byte（微信）/ char（小红书） */
  titleUnit: TitleUnit
  /** 摘要上限（字符）；无独立摘要为 null */
  digestMax: number | null
  /** 正文上限（字符）；无硬上限为 null */
  bodyMax: number | null
  /** 封面 / 图片最少张数 */
  imageMin: number
  /** 图片最多张数；无上限为 null */
  imageMax: number | null
  /** 单图大小上限（字节）；无限制为 null */
  imageMaxBytes: number | null
  /** 话题标签上限数量；无限制为 null */
  maxTopics: number | null
  /** 单个话题标签长度上限（字符）；无限制为 null */
  maxTopicLen: number | null
  /** 违禁 / 敏感词 */
  forbiddenWords: string[]
  /** True 表示规则值为 PRD 默认值，待官方核实（仅代码自说明，不影响校验） */
  unconfirmed: boolean
}

/** 平台约束唯一真源（镜像后端 PLATFORM_RULES） */
export const PLATFORM_RULES: Record<Platform, PlatformRule> = {
  wechat: {
    titleMax: 64, // 64 字节，纯中文≈21字
    titleUnit: 'byte',
    digestMax: 120, // 摘要 ≤120 字符
    bodyMax: null, // 图文正文无硬性字数上限
    imageMin: 1, // 封面必填
    imageMax: null,
    imageMaxBytes: 2 * 1024 * 1024, // 单图 ≤2MB
    maxTopics: null, // 微信以 #标签 文本嵌入正文，无独立话题限制
    maxTopicLen: null,
    forbiddenWords: [], // 公众号可正常出现「出租/租房」等合规词
    unconfirmed: false,
  },
  xiaohongshu: {
    titleMax: 20, // 标题 ≤20 字符
    titleUnit: 'char',
    digestMax: null, // 无独立摘要
    bodyMax: 1000, // 正文 ≤1000 字符（待核实）
    imageMin: 1, // 至少 1 张图
    imageMax: 18, // 单篇最多 18 张（待核实）
    imageMaxBytes: null,
    maxTopics: 10, // 话题 ≤10 个（待核实）
    maxTopicLen: 20, // 单个话题 ≤20 字符（待核实）
    forbiddenWords: ['出租', '租房', '月租', '租金', '招租', '房东'], // 规避直白租赁词
    unconfirmed: true, // 小红书规则为 PRD 默认值，待官方核实
  },
}

/** 计算字符串的 UTF-8 字节长度（与后端 len(s.encode('utf-8')) 一致） */
function byteLength(text: string): number {
  if (typeof TextEncoder !== 'undefined') {
    return new TextEncoder().encode(text).length
  }
  // 兜底（极老环境）：粗略按 UTF-8 估计
  let bytes = 0
  for (let i = 0; i < text.length; i++) {
    const code = text.charCodeAt(i)
    if (code < 0x80) bytes += 1
    else if (code < 0x800) bytes += 2
    else if (code >= 0xd800 && code <= 0xdbff) {
      // 代理对（emoji 等），占 4 字节
      bytes += 4
      i++
    } else bytes += 3
  }
  return bytes
}

export interface CountResult {
  /** 当前计量值（字节或字符） */
  count: number
  /** 上限 */
  max: number
  /** 计量口径 */
  unit: TitleUnit
  /** 剩余（max - count，可为负） */
  remaining: number
  /** 是否超限 */
  overLimit: boolean
}

/**
 * 统计标题长度，按平台计量口径（微信=字节 / 小红书=字符）。
 * 返回值结构与后端 platform_rules.count_title 保持一致。
 */
export function countTitle(text: string, platform: Platform): CountResult {
  const rule = PLATFORM_RULES[platform]
  const count = rule.titleUnit === 'byte' ? byteLength(text || '') : (text || '').length
  const remaining = rule.titleMax - count
  return {
    count,
    max: rule.titleMax,
    unit: rule.titleUnit,
    remaining,
    overLimit: count > rule.titleMax,
  }
}

export interface BodyCountResult {
  count: number
  max: number | null
  remaining: number | null
  overLimit: boolean
}

/**
 * 统计正文字符长度。
 * 微信正文无硬上限（bodyMax=null），此时返回实际字符数且不触发超限。
 */
export function countBody(text: string, platform: Platform): BodyCountResult {
  const rule = PLATFORM_RULES[platform]
  const count = (text || '').length
  if (rule.bodyMax === null) {
    return { count, max: null, remaining: null, overLimit: false }
  }
  const remaining = rule.bodyMax - count
  return { count, max: rule.bodyMax, remaining, overLimit: count > rule.bodyMax }
}

/** 平台中文名（用于提示展示） */
export function platformLabel(platform: Platform): string {
  return platform === 'xiaohongshu' ? '小红书' : '微信'
}
