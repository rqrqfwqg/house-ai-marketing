/**
 * 房源 API
 */
import client from './client'
import type {
  House,
  HouseCreate,
  HouseListResponse,
  UploadResponse,
} from '@/types'

/**
 * 获取健康检查
 */
export async function checkHealth(): Promise<{ status: string; message: string }> {
  const { data } = await client.get('/health')
  return data
}

/**
 * 上传房源（多图片 + 房源信息）
 */
export async function uploadHouse(
  images: File[],
  houseInfo: HouseCreate
): Promise<UploadResponse> {
  const formData = new FormData()
  images.forEach((file) => {
    formData.append('images', file)
  })
  formData.append('house_info', JSON.stringify(houseInfo))

  const { data } = await client.post('/houses/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return data
}

/**
 * 获取房源列表
 */
export async function getHouses(
  skip: number = 0,
  limit: number = 100
): Promise<HouseListResponse> {
  const { data } = await client.get('/houses', {
    params: { skip, limit },
  })
  return data
}

/**
 * 获取房源详情
 */
export async function getHouse(id: number): Promise<House> {
  const { data } = await client.get(`/houses/${id}`)
  return data
}

/**
 * 删除房源
 */
export async function deleteHouse(id: number): Promise<void> {
  await client.delete(`/houses/${id}`)
}
