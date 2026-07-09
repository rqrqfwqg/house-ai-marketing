/**
 * 客户端图片压缩工具（基于原生 Canvas，不引入任何第三方依赖）
 *
 * 用于在用户选图后、上传前，于浏览器端对每张图片进行压缩，
 * 减小图片体积，从而降低服务器存储空间占用与上传流量消耗。
 */

/** 压缩参数 */
export interface CompressOptions {
  /** 长边最大像素，默认 1920 */
  maxEdge?: number
  /** JPEG 输出质量 0~1，默认 0.8 */
  quality?: number
}

/**
 * 使用 canvas 将图片压缩为「限定长边 + 指定质量」的 JPEG File。
 *
 * - 非图片文件：直接原样返回，避免阻断上传流程。
 * - 压缩/解码失败：原样返回原文件，保证上传可用性。
 *
 * @param file 原始图片文件
 * @param opts 压缩选项（maxEdge / quality）
 * @returns 压缩后的 JPEG File（失败时返回原 file）
 */
export async function compressImage(file: File, opts: CompressOptions = {}): Promise<File> {
  const maxEdge: number = opts.maxEdge ?? 1920
  const quality: number = opts.quality ?? 0.8

  // 非图片类型（如视频、文档）不处理
  if (!file.type.startsWith('image/')) return file

  let bitmap: ImageBitmap
  try {
    bitmap = await createImageBitmap(file)
  } catch {
    return file
  }

  let width = bitmap.width
  let height = bitmap.height
  const scale = Math.min(1, maxEdge / Math.max(width, height))
  width = Math.round(width * scale)
  height = Math.round(height * scale)

  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    bitmap.close?.()
    return file
  }
  ctx.drawImage(bitmap, 0, 0, width, height)
  bitmap.close?.()

  const blob: Blob | null = await new Promise<Blob | null>((resolve) => {
    canvas.toBlob((b) => resolve(b), 'image/jpeg', quality)
  })
  if (!blob) return file

  const ext = 'jpg'
  const baseName = file.name.replace(/\.[^.]+$/, '') || 'image'
  const newName = `${baseName}.${ext}`
  return new File([blob], newName, { type: 'image/jpeg' })
}
