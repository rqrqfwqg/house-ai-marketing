/*
 * 房源相关API调用
 * 封装：上传房源、获取列表、获取详情、删除房源
 */
import apiClient from './api';
import type { House, HouseCreate, HouseListResponse, UploadResponse } from '../types/house';

// 重新导出类型以便其他模块使用
export type { HouseCreate };

/**
 * 上传房源（图片 + 信息）
 * @param images - 图片文件列表
 * @param houseInfo - 房源基本信息（可选）
 * @returns 上传响应（包含房源ID和图片路径）
 */
export async function uploadHouse(
  images: File[],
  houseInfo?: HouseCreate
): Promise<UploadResponse> {
  // 创建FormData
  const formData = new FormData();
  
  // 添加图片文件
  images.forEach((image) => {
    formData.append('images', image);
  });
  
  // 添加房源信息（如果有）
  if (houseInfo) {
    formData.append('house_info', JSON.stringify(houseInfo));
  }
  
  // 发送请求
  const response = await apiClient.post<UploadResponse>('/houses/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  
  return response.data;
}

/**
 * 获取房源列表
 * @param params - 分页参数
 * @returns 房源列表和总数
 */
export async function getHouses(params?: {
  skip?: number;
  limit?: number;
}): Promise<HouseListResponse> {
  const response = await apiClient.get<HouseListResponse>('/houses', {
    params,
  });
  
  return response.data;
}

/**
 * 获取房源详情
 * @param houseId - 房源ID
 * @returns 房源详情
 */
export async function getHouse(houseId: number): Promise<House> {
  const response = await apiClient.get<House>(`/houses/${houseId}`);
  return response.data;
}

/**
 * 删除房源
 * @param houseId - 房源ID
 * @returns void
 */
export async function deleteHouse(houseId: number): Promise<void> {
  await apiClient.delete(`/houses/${houseId}`);
}
