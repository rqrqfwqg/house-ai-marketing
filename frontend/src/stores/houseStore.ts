/*
 * 房源状态管理（Zustand）
 * 管理：当前房源、图片列表、加载状态
 */
import { create } from 'zustand';
import { House } from '../types/house';

interface HouseStore {
  // 状态
  currentHouse: House | null;
  images: File[];
  loading: boolean;
  error: string | null;

  // 操作方法
  setCurrentHouse: (house: House | null) => void;
  setImages: (images: File[]) => void;
  addImages: (newImages: File[]) => void;
  removeImage: (index: number) => void;
  clearImages: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const useHouseStore = create<HouseStore>((set) => ({
  // 初始状态
  currentHouse: null,
  images: [],
  loading: false,
  error: null,

  // 操作方法实现
  setCurrentHouse: (house) => set({ currentHouse: house }),

  setImages: (images) => set({ images }),

  addImages: (newImages) =>
    set((state) => ({
      images: [...state.images, ...newImages].slice(0, 10), // 最多10张
    })),

  removeImage: (index) =>
    set((state) => ({
      images: state.images.filter((_, i) => i !== index),
    })),

  clearImages: () => set({ images: [] }),

  setLoading: (loading) => set({ loading }),

  setError: (error) => set({ error }),

  reset: () =>
    set({
      currentHouse: null,
      images: [],
      loading: false,
      error: null,
    }),
}));

export default useHouseStore;
