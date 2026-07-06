/*
 * 历史记录卡片组件
 * 功能：显示单条历史记录（房源+文案+发布状态）
 */
import React from 'react';
import { Trash2, FileText, Send } from 'lucide-react';
import { House } from '../types/house';
import { Script } from '../types/script';
import { PublishLog } from '../types/api';

interface HistoryCardProps {
  house: House;
  scripts: Script[];
  publishLogs: PublishLog[];
  onDelete: (houseId: number) => void;
  onView: (scriptId: number) => void;
  onGenerate: (houseId: number) => void;
}

const HistoryCard: React.FC<HistoryCardProps> = ({
  house,
  scripts,
  publishLogs,
  onDelete,
  onView,
  onGenerate,
}) => {
  return (
    <div className="bg-white p-6 rounded-lg shadow">
      {/* 房源信息 */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-bold">{house.title || '未命名房源'}</h3>
          <p className="text-sm text-gray-600 mt-1">
            {house.address && `📍 ${house.address}`}
            {house.rent && ` | 💰 ${house.rent}元/月`}
            {house.rooms && ` | 🏠 ${house.rooms}`}
          </p>
        </div>

        <button
          onClick={() => onDelete(house.id)}
          className="text-red-600 hover:text-red-800"
          title="删除"
        >
          <Trash2 size={20} />
        </button>
      </div>

      {/* 图片预览 */}
      {house.images.length > 0 && (
        <div className="flex gap-2 mb-4 overflow-x-auto">
          {house.images.slice(0, 3).map((image, index) => (
            <img
              key={index}
              src={image}
              alt={`房源图片 ${index + 1}`}
              className="h-20 w-20 object-cover rounded-md"
            />
          ))}
        </div>
      )}

      {/* 文案列表 */}
      {scripts.length > 0 && (
        <div className="mb-4">
          <h4 className="font-semibold mb-2 flex items-center gap-2">
            <FileText size={16} />
            生成文案 ({scripts.length})
          </h4>
          {scripts.map((script) => (
            <div
              key={script.id}
              className="p-3 bg-gray-50 rounded-md cursor-pointer hover:bg-gray-100 mb-2"
              onClick={() => onView(script.id)}
            >
              <p className="font-medium">{script.title}</p>
              <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                {script.body}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* 发布记录 */}
      {publishLogs.length > 0 && (
        <div className="mb-4">
          <h4 className="font-semibold mb-2 flex items-center gap-2">
            <Send size={16} />
            发布记录 ({publishLogs.length})
          </h4>
          {publishLogs.map((log) => (
            <div
              key={log.id}
              className={`text-sm p-2 rounded-md mb-1 ${
                log.status === 'success' || log.status === 'draft_created'
                  ? 'bg-green-50 text-green-700'
                  : log.status === 'failed'
                  ? 'bg-red-50 text-red-700'
                  : 'bg-gray-50 text-gray-700'
              }`}
            >
              <span className="font-medium">
                {log.platform === 'xiaohongshu' ? '小红书' : '微信公众号'}
              </span>
              {' - '}
              <span>
                {log.status === 'success' && '发布成功'}
                {log.status === 'draft_created' && '草稿已创建'}
                {log.status === 'failed' && `发布失败：${log.error_msg}`}
                {log.status === 'pending' && '待发布'}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* 操作按钮 */}
      <div className="flex gap-2">
        <button
          onClick={() => onGenerate(house.id)}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
        >
          生成文案
        </button>
        {scripts.length > 0 && (
          <button
            onClick={() => onView(scripts[0].id)}
            className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm"
          >
            查看文案
          </button>
        )}
      </div>
    </div>
  );
};

export default HistoryCard;
