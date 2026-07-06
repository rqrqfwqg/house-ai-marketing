/*
 * 文案生成页面
 * 功能：选择模板风格、调用AI生成、显示结果
 */
import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Sparkles, RefreshCw, ArrowRight } from 'lucide-react';
import { generateScript, Script } from '../services/scriptApi';
import { ScriptGenerateRequest } from '../types/script';
import { TemplateStyle, TEMPLATE_STYLES } from '../types/script';

const GeneratePage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const houseId = searchParams.get('house_id');

  // 状态
  const [templateStyle, setTemplateStyle] = useState<TemplateStyle>('professional');
  const [loading, setLoading] = useState(false);
  const [generatedScript, setGeneratedScript] = useState<Script | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 如果没有house_id，重定向到上传页面
  useEffect(() => {
    if (!houseId) {
      navigate('/upload');
    }
  }, [houseId, navigate]);

  // 生成文案
  const handleGenerate = async () => {
    if (!houseId) return;

    setLoading(true);
    setError(null);

    try {
      const request: ScriptGenerateRequest = {
        house_id: parseInt(houseId),
        template_style: templateStyle,
      };

      const script = await generateScript(request);
      setGeneratedScript(script);
    } catch (err: any) {
      setError(err.response?.data?.detail || '生成失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  // 跳转到预览页面
  const handlePreview = () => {
    if (generatedScript) {
      navigate(`/preview/${generatedScript.id}`);
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <h2 className="text-2xl font-bold mb-6">AI生成文案</h2>

      {/* 房源ID显示 */}
      {houseId && (
        <div className="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded-md mb-6">
          当前房源ID：{houseId}
        </div>
      )}

      {/* 模板风格选择 */}
      <div className="bg-white p-6 rounded-lg shadow mb-6">
        <h3 className="text-lg font-semibold mb-4">选择文案风格</h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {(Object.keys(TEMPLATE_STYLES) as TemplateStyle[]).map((style) => (
            <div
              key={style}
              className={`border-2 rounded-lg p-4 cursor-pointer transition-colors ${
                templateStyle === style
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-blue-300'
              }`}
              onClick={() => setTemplateStyle(style)}
            >
              <h4 className="font-semibold text-lg mb-2">{TEMPLATE_STYLES[style].label}</h4>
              <p className="text-sm text-gray-600">{TEMPLATE_STYLES[style].description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* 生成按钮 */}
      <div className="flex justify-center mb-6">
        <button
          onClick={handleGenerate}
          disabled={loading}
          className={`px-8 py-3 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-md hover:from-blue-700 hover:to-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 flex items-center gap-2 ${
            loading ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {loading ? (
            <>
              <RefreshCw size={20} className="animate-spin" />
              AI生成中...
            </>
          ) : (
            <>
              <Sparkles size={20} />
              生成文案
            </>
          )}
        </button>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-6">
          {error}
        </div>
      )}

      {/* 生成结果预览 */}
      {generatedScript && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">生成结果</h3>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">标题</label>
              <p className="text-xl font-bold text-gray-900">{generatedScript.title}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">正文</label>
              <div className="prose max-w-none">
                {generatedScript.body.split('\n').map((line, index) => (
                  <p key={index} className="mb-2">
                    {line}
                  </p>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">标签</label>
              <div className="flex flex-wrap gap-2">
                {generatedScript.tags.map((tag, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* 预览按钮 */}
          <div className="mt-6 flex justify-end">
            <button
              onClick={handlePreview}
              className="px-6 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 flex items-center gap-2"
            >
              预览并编辑
              <ArrowRight size={20} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default GeneratePage;
