/*
 * 图片上传页面
 * 功能：多图上传、房源信息表单、提交到后端
 * 已移除 antd-mobile，使用原生 HTML + Tailwind
 */
import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ImageUploader from '../components/ImageUploader'
import { uploadHouse, HouseCreate } from '../services/houseApi'

const UploadPage: React.FC = () => {
  const navigate = useNavigate()

  const [images, setImages] = useState<File[]>([])
  const [houseInfo, setHouseInfo] = useState<HouseCreate>({
    title: '',
    address: '',
    rent: undefined,
    rooms: '',
    area: undefined,
    floor: '',
    tags: [],
  })
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null)

  // 显示提示
  const showToast = (msg: string, type: 'success' | 'error' = 'error') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 2500)
  }

  // 处理表单提交
  const handleSubmit = async () => {
    if (images.length === 0) {
      showToast('请至少上传一张图片')
      return
    }

    if (!houseInfo.title || !houseInfo.address) {
      showToast('请填写房源标题和地址')
      return
    }

    setLoading(true)

    try {
      const response = await uploadHouse(images, houseInfo)
      showToast('上传成功！', 'success')
      setTimeout(() => {
        navigate(`/generate?house_id=${response.id}`)
      }, 1000)
    } catch (err: any) {
      showToast(err.response?.data?.detail || '上传失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="upload-page">
      {/* Toast 提示 */}
      {toast && (
        <div className={`fixed top-16 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-lg shadow-lg text-sm text-white ${toast.type === 'success' ? 'bg-green-500' : 'bg-red-500'}`}>
          {toast.msg}
        </div>
      )}

      {/* 图片上传区域 */}
      <div className="section">
        <div className="section-title">房源图片</div>
        <div className="section-desc">上传清晰的房源照片，最多9张</div>
        <ImageUploader images={images} onImagesChange={setImages} maxImages={9} />
      </div>

      {/* 房源信息表单 */}
      <div className="section">
        <div className="section-title">房源信息</div>

        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">房源标题</label>
            <input
              type="text"
              placeholder="例如：阳光充足精装两居室"
              value={houseInfo.title || ''}
              onChange={e => setHouseInfo({ ...houseInfo, title: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-base"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">地址</label>
            <input
              type="text"
              placeholder="例如：海淀区中关村大街"
              value={houseInfo.address || ''}
              onChange={e => setHouseInfo({ ...houseInfo, address: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-base"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">月租金（元）</label>
              <input
                type="number"
                placeholder="例如：5000"
                value={houseInfo.rent?.toString() || ''}
                onChange={e => setHouseInfo({ ...houseInfo, rent: parseFloat(e.target.value) || undefined })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-base"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">户型</label>
              <input
                type="text"
                placeholder="例如：2室1厅"
                value={houseInfo.rooms || ''}
                onChange={e => setHouseInfo({ ...houseInfo, rooms: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-base"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">面积（平米）</label>
              <input
                type="number"
                placeholder="例如：80"
                value={houseInfo.area?.toString() || ''}
                onChange={e => setHouseInfo({ ...houseInfo, area: parseFloat(e.target.value) || undefined })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-base"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">楼层</label>
              <input
                type="text"
                placeholder="例如：中层/15层"
                value={houseInfo.floor || ''}
                onChange={e => setHouseInfo({ ...houseInfo, floor: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-base"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">标签（用逗号分隔）</label>
            <input
              type="text"
              placeholder="例如：近地铁,精装修,拎包入住"
              value={(houseInfo.tags || []).join(',')}
              onChange={e => setHouseInfo({ ...houseInfo, tags: e.target.value.split(',').map(t => t.trim()).filter(t => t) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-base"
            />
          </div>
        </div>
      </div>

      {/* 提交按钮 */}
      <div className="submit-section">
        <button
          onClick={handleSubmit}
          disabled={loading}
          className={`w-full py-3 rounded-lg text-white text-base font-medium ${loading ? 'bg-gray-400' : 'bg-blue-600 hover:bg-blue-700 active:bg-blue-800'}`}
        >
          {loading ? '上传中...' : '下一步：生成文案'}
        </button>
      </div>
    </div>
  )
}

export default UploadPage
