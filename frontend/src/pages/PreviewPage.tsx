/*
 * 文案预览页面
 * 功能：预览文案、编辑文案、选择发布平台
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Edit, ArrowRight } from 'lucide-react';
import { getScript, updateScript } from '../services/scriptApi';
import { Script } from '../types/script';
import ScriptEditor from '../components/ScriptEditor';

const PreviewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [script, setScript] = useState<Script | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);

  // 加载文案
  useEffect(() => {
    if (!id) return;

    const loadScript = async () => {
      try {
        setLoading(true);
        const data = await getScript(parseInt(id));
        setScript(data);
      } catch (err: any) {
        setError(err.response?.data?.detail || '加载失败');
      } finally {
        setLoading(false);
      }
    };

    loadScript();
  }, [id]);

  // 保存编辑
  const handleSaveEdit = async (updatedScript: Script) => {
    try {
      const saved = await updateScript(updatedScript.id, {
        title: updatedScript.title,
        body: updatedScript.body,
        tags: updatedScript.tags,
      });

      setScript(saved);
      setIsEditing(false);
      alert('保存成功！');
    } catch (err: any) {
      alert(err.response?.data?.detail || '保存失败');
    }
  };

  // 跳转到发布页面
  const handlePublish = () => {
    if (script) {
      navigate(`/publish?script_id=${script.id}`);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <p className="text-center text-gray-500">加载中...</p>
      </div>
    );
  }

  if (error || !script) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error || '文案不存在'}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <h2 className="text-2xl font-bold mb-6">文案预览</h2>

      {!isEditing ? (
        /* 预览模式 */
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="mb-6">
            <h3 className="text-xl font-bold mb-4">{script.title}</h3>
            <div className="prose max-w-none">
              <div dangerouslySetInnerHTML={{ __html: script.body }} />
            </div>
          </div>

          <div className="mb-6">
            <h4 className="font-semibold mb-2">标签</h4>
            <div className="flex flex-wrap gap-2">
              {script.tags.map((tag, index) => (
                <span
                  key={index}
                  className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>

          <div className="flex justify-between">
            <button
              onClick={() => setIsEditing(true)}
              className="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 flex items-center gap-2"
            >
              <Edit size={20} />
              编辑文案
            </button>

            <button
              onClick={handlePublish}
              className="px-6 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 flex items-center gap-2"
            >
              选择平台发布
              <ArrowRight size={20} />
            </button>
          </div>
        </div>
      ) : (
        /* 编辑模式 */
        <ScriptEditor script={script} onSave={handleSaveEdit} />
      )}
    </div>
  );
};

export default PreviewPage;
