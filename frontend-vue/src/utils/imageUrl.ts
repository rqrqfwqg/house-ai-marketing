/**
 * 图片 URL 前缀解析工具
 *
 * 后端图片存储相对路径固定为 `/uploads/...`，
 * 而生产环境整体部署在子路径 `/house-ai/` 下，
 * 真实可访问地址为 `http(s)://域名/house-ai/uploads/...`。
 *
 * 该函数统一把「以 / 开头的相对路径」拼上部署子路径前缀，
 * 避免子路径部署下图片 404（黑图）问题。
 */

/**
 * 解析图片 URL，确保子路径部署下的相对路径可被正确访问。
 * @param img 图片地址：可能是完整 URL、data: 内联图、或以 / 开头的相对路径
 * @returns 经部署前缀处理后的图片地址
 */
export function resolveImageUrl(img: string): string {
  if (!img) return img
  // 完整 URL / 内联图直接返回，无需拼接前缀
  if (img.startsWith('http://') || img.startsWith('https://') || img.startsWith('data:')) {
    return img
  }
  // 生产 '/house-ai'，开发 ''（vite dev 默认无 VITE_BASE）
  const base = (import.meta.env.VITE_BASE || '').replace(/\/+$/, '')
  if (img.startsWith('/')) {
    if (base && !img.startsWith(base)) return base + img
    return img
  }
  return img
}
