/*
 * 房源相关类型定义
 * 定义：House（房源）、HouseCreate（创建请求）、HouseResponse（响应）
 */

/**
 * 房源信息接口
 * 对应后端 HouseResponse
 */
export interface House {
  id: number;
  title?: string;
  address?: string;
  rent?: number;
  rooms?: string;
  area?: number;
  floor?: string;
  tags: string[];
  images: string[];  // 图片路径列表
  created_at: string;  // ISO 8601 格式
  updated_at: string;
}

/**
 * 房源创建请求接口
 * 对应后端 HouseCreate
 */
export interface HouseCreate {
  title?: string;
  address?: string;
  rent?: number;
  rooms?: string;
  area?: number;
  floor?: string;
  tags?: string[];
}

/**
 * 房源列表响应接口
 */
export interface HouseListResponse {
  items: House[];
  total: number;
}

/**
 * 图片上传响应接口
 */
export interface UploadResponse {
  id: number;
  images: string[];
  message: string;
}
