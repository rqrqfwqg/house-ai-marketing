/*
 * 图片上传组件（完全自定义）
 * 功能：多图上传、预览、删除
 * 使用 base64 预览，永不失效；9 宫格布局（最多 9 张）
 */
import React, { useRef, useState, useCallback, useEffect } from 'react';

interface ImageItem {
  file: File;
  preview: string; // base64 data URL
}

interface ImageUploaderProps {
  images: File[];           // 已选择的图片文件（受控）
  onImagesChange: (images: File[]) => void;
  maxImages?: number;
}

const ImageUploader: React.FC<ImageUploaderProps> = ({
  images,
  onImagesChange,
  maxImages = 9,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  // 内部维护 {file, preview} 列表，与父组件 images 同步
  const [items, setItems] = useState<ImageItem[]>([]);

  // 本地 toast（替代 antd-mobile 的 Toast）
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null);
  const showToast = (msg: string, type: 'success' | 'error' = 'error') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 2500);
  };

  // 当父组件 images 变化时，同步重置 items（如清空场景）
  // 用 JSON.stringify(images.map(f=>f.name+f.size)) 做指纹对比，避免死循环
  const imagesRef = useRef<string>('');
  useEffect(() => {
    const fingerprint = JSON.stringify(images.map(f => f.name + '|' + f.size + '|' + f.lastModified));
    if (fingerprint === imagesRef.current) return;
    imagesRef.current = fingerprint;

    // 如果 images 为空，清空 items
    if (images.length === 0) {
      // 释放旧的 base64（其实 base64 存在内存中，无需 revoke）
      setItems([]);
      return;
    }

    // 尝试复用已有 items 中的 preview（避免重复读文件）
    const existingMap = new Map<string, string>();
    items.forEach(item => {
      const key = item.file.name + '|' + item.file.size + '|' + item.file.lastModified;
      existingMap.set(key, item.preview);
    });

    const newItems: ImageItem[] = [];
    let needsAsync = false;

    for (const file of images) {
      const key = file.name + '|' + file.size + '|' + file.lastModified;
      if (existingMap.has(key)) {
        newItems.push({ file, preview: existingMap.get(key)! });
      } else {
        needsAsync = true;
        // 稍后异步生成 preview
      }
    }

    if (!needsAsync) {
      setItems(newItems);
      return;
    }

    // 有新增文件，需要异步读取
    const readAll = async () => {
      const result: ImageItem[] = [];
      for (const file of images) {
        const key = file.name + '|' + file.size + '|' + file.lastModified;
        if (existingMap.has(key)) {
          result.push({ file, preview: existingMap.get(key)! });
        } else {
          const preview = await fileToBase64(file);
          result.push({ file, preview });
        }
      }
      setItems(result);
    };
    readAll();
  }, [images]);

  // File → base64
  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = () => reject(new Error('读取文件失败'));
      reader.readAsDataURL(file);
    });
  };

  // 处理文件选择
  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const currentFiles = items.map(it => it.file);
    let newFiles = [...currentFiles];
    let newItemsList = [...items];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];

      if (!file.type.startsWith('image/')) {
        showToast(`"${file.name}" 不是图片`);
        continue;
      }
      if (file.size > 10 * 1024 * 1024) {
        showToast(`"${file.name}" 超过 10MB`);
        continue;
      }
      if (newFiles.length >= maxImages) {
        showToast(`最多 ${maxImages} 张图片`);
        break;
      }

      try {
        const preview = await fileToBase64(file);
        newFiles.push(file);
        newItemsList.push({ file, preview });
      } catch {
        showToast('图片读取失败');
      }
    }

    onImagesChange(newFiles);
    setItems(newItemsList);
    e.target.value = '';
  }, [items, maxImages, onImagesChange]);

  // 删除
  const handleDelete = useCallback((index: number) => {
    const newItemsList = items.filter((_, i) => i !== index);
    setItems(newItemsList);
    onImagesChange(newItemsList.map(it => it.file));
  }, [items, onImagesChange]);

  const triggerFileSelect = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  return (
    <div className="w-full">
      {/* 隐藏 input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        multiple
        onChange={handleFileSelect}
        style={{ display: 'none' }}
      />

      {/* 9 宫格 */}
      <div className="grid grid-cols-3 gap-2">
        {items.map((item, index) => (
          <div key={index} className="relative aspect-square rounded-lg overflow-hidden bg-gray-100">
            <img
              src={item.preview}
              alt={`图片 ${index + 1}`}
              className="w-full h-full object-cover"
            />
            {/* 删除按钮 */}
            <button
              type="button"
              onClick={() => handleDelete(index)}
              className="absolute top-1 right-1 w-6 h-6 bg-red-500/80 text-white rounded-full flex items-center justify-center text-sm font-bold hover:bg-red-600"
            >
              ×
            </button>
          </div>
        ))}

        {/* 上传按钮 */}
        {items.length < maxImages && (
          <div
            onClick={triggerFileSelect}
            className="aspect-square rounded-lg border-2 border-dashed border-gray-300 flex flex-col items-center justify-center cursor-pointer hover:border-blue-500 hover:bg-blue-50 active:bg-blue-100 transition-colors"
          >
            <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            <span className="text-xs text-gray-500 mt-1">添加图片</span>
          </div>
        )}
      </div>

      <p className="text-xs text-gray-500 mt-2">
        支持 JPG、PNG、WebP，最多 {maxImages} 张，单张 ≤ 10MB
      </p>

      {toast && (
        <div className={`fixed top-4 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-lg text-white text-sm shadow-lg ${toast.type === 'success' ? 'bg-green-500' : 'bg-red-500'}`}>
          {toast.msg}
        </div>
      )}
    </div>
  );
};

export default ImageUploader;
