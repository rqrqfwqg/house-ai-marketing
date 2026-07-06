/*
 * 历史记录页面
 * 功能：查看历史记录、删除记录、跳转到详情
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Trash2, FileText, Send } from 'lucide-react';
import { getHouses, deleteHouse } from '../services/houseApi';
import { getScripts } from '../services/scriptApi';
import { getPublishLogs } from '../services/publishApi';
import { House } from '../types/house';
import { Script } from '../types/script';
import { PublishLog } from '../types/api';

interface HistoryItem {
  house: House;
  scripts: Script[];
  publish_logs: PublishLog[];
}

const HistoryPage: React.FC = () => {
  const navigate = useNavigate();

  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 加载历史记录
  const loadHistory = async () => {
    try {
      setLoading(true);
      setError(null);

      // 获取房源列表
      const houses = await getHouses({ limit: 100 });

      // 为每个房源获取文案和发布记录
      const historyItems: HistoryItem[] = [];

      for (const house of houses.items) {
        const scripts = await getScripts({ house_id: house.id });
        const logs = await getPublishLogs(house.id);

        historyItems.push({
          house,
          scripts: scripts.items,
          publish_logs: logs,
        });
      }

      setHistory(historyItems);
    } catch (err: any) {
      setError(err.response?.data?.detail || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  // 删除记录
  const handleDelete = async (houseId: number) => {
    if (!confirm('确定要删除这条记录吗？')) return;

    try {
      await deleteHouse(houseId);
      alert('删除成功！');
      loadHistory(); // 重新加载
    } catch (err: any) {
      alert(err.response?.data?.detail || '删除失败');
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <p className="text-center text-gray-500">加载中...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <h2 className="text-2xl font-bold mb-6">历史记录</h2>

      {history.length === 0 ? (
        <div className="bg-white p-6 rounded-lg shadow text-center">
          <p className="text-gray-500">暂无历史记录</p>
          <button
            onClick={() => navigate('/upload')}
            className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            去上传房源
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {history.map((item) => (
            <div key={item.house.id} className="bg-white p-6 rounded-lg shadow">
              {/* 房源信息 */}
              <div className="flex justify-between items-start mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-bold">{item.house.title || '未命名房源'}</h3>
                  <p className="text-sm text-gray-600 mt-1">
                    {item.house.address && `📍 ${item.house.address}`}
                    {item.house.rent && ` | 💰 ${item.house.rent}元/月`}
                    {item.house.rooms && ` | 🏠 ${item.house.rooms}`}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    创建时间：{new Date(item.house.created_at).toLocaleString()}
                  </p>
                </div>

                <button
                  onClick={() => handleDelete(item.house.id)}
                  className="text-red-600 hover:text-red-800"
                  title="删除"
                >
                  <Trash2 size={20} />
                </button>
              </div>

              {/* 图片预览 */}
              {item.house.images.length > 0 && (
                <div className="flex gap-2 mb-4 overflow-x-auto">
                  {item.house.images.slice(0, 3).map((image, index) => (
                    <img
                      key={index}
                      src={image}
                      alt={`房源图片 ${index + 1}`}
                      className="h-20 w-20 object-cover rounded-md"
                    />
                  ))}
                  {item.house.images.length > 3 && (
                    <div className="h-20 w-20 bg-gray-200 rounded-md flex items-center justify-center text-gray-600">
                      +{item.house.images.length - 3}
                    </div>
                  )}
                </div>
              )}

              {/* 文案列表 */}
              {item.scripts.length > 0 && (
                <div className="mb-4">
                  <h4 className="font-semibold mb-2 flex items-center gap-2">
                    <FileText size={16} />
                    生成文案 ({item.scripts.length})
                  </h4>
                  <div className="space-y-2">
                    {item.scripts.map((script) => (
                      <div
                        key={script.id}
                        className="p-3 bg-gray-50 rounded-md cursor-pointer hover:bg-gray-100"
                        onClick={() => navigate(`/preview/${script.id}`)}
                      >
                        <p className="font-medium">{script.title}</p>
                        <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                          {script.body}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 发布记录 */}
              {item.publish_logs.length > 0 && (
                <div>
                  <h4 className="font-semibold mb-2 flex items-center gap-2">
                    <Send size={16} />
                    发布记录 ({item.publish_logs.length})
                  </h4>
                  <div className="space-y-1">
                    {item.publish_logs.map((log) => (
                      <div
                        key={log.id}
                        className={`text-sm p-2 rounded-md ${
                          log.status === 'success' || log.status === 'draft_created'
                            ? 'bg-green-50 text-green-700'
                            : log.status === 'failed'
                            ? 'bg-red-50 text-red-700'
                            : 'bg-gray-50 text-gray-700'
                        }`}
                      >
                        <span className="font-medium">{log.platform === 'xiaohongshu' ? '小红书' : '微信公众号'}</span>
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
                </div>
              )}

              {/* 操作按钮 */}
              <div className="mt-4 flex gap-2">
                <button
                  onClick={() => navigate(`/generate?house_id=${item.house.id}`)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
                >
                  生成文案
                </button>
                {item.scripts.length > 0 && (
                  <button
                    onClick={() => navigate(`/preview/${item.scripts[0].id}`)}
                    className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm"
                  >
                    查看文案
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default HistoryPage;
