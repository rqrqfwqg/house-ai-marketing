/*
 * 发布选择页面
 * 功能：选择发布平台、执行发布、显示结果、登录过期时展示二维码
 */
import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Send, CheckCircle, XCircle, Loader } from 'lucide-react';
import { getScript } from '../services/scriptApi';
import { Script } from '../types/script';
import { publishToXiaohongshu, createWechatDraft, PublishResponse } from '../services/publishApi';
import { Platform } from '../types/api';
import XhsQrCodeModal from '../components/XhsQrCodeModal';

const PublishPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const scriptId = searchParams.get('script_id');

  const [script, setScript] = useState<Script | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedPlatform, setSelectedPlatform] = useState<Platform | null>(null);
  const [publishing, setPublishing] = useState(false);
  const [publishResult, setPublishResult] = useState<PublishResponse | null>(null);

  // 小红书登录二维码弹窗
  const [showQrModal, setShowQrModal] = useState(false);

  // 本地 toast（替代 antd-mobile 的 Toast）
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null);
  const showToast = (msg: string, type: 'success' | 'error' = 'error') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 2500);
  };

  // 加载文案
  useEffect(() => {
    if (!scriptId) {
      setError('缺少script_id参数');
      setLoading(false);
      return;
    }

    const loadScript = async () => {
      try {
        setLoading(true);
        const data = await getScript(parseInt(scriptId));
        setScript(data);
      } catch (err: any) {
        setError(err.response?.data?.detail || '加载失败');
      } finally {
        setLoading(false);
      }
    };

    loadScript();
  }, [scriptId]);

  // 判断是否登录过期（根据错误信息判断）
  const isLoginExpired = (errorMsg: string): boolean => {
    const keywords = ['登录', 'login', '未登录', 'token', 'auth', '授权'];
    return keywords.some(kw => errorMsg.toLowerCase().includes(kw.toLowerCase()));
  };

  // 执行发布
  const handlePublish = async () => {
    if (!script || !selectedPlatform) return;

    setPublishing(true);
    setPublishResult(null);

    try {
      let result: PublishResponse;

      if (selectedPlatform === 'xiaohongshu') {
        result = await publishToXiaohongshu({
          script_id: script.id,
          images: [], // TODO: 从房源获取图片
        });
      } else {
        result = await createWechatDraft({
          script_id: script.id,
          images: [], // TODO: 从房源获取图片
        });
      }

      setPublishResult(result);

      // 如果是小红书且登录过期，弹出二维码
      if (!result.success && selectedPlatform === 'xiaohongshu') {
        const errorMsg = result.error || '';
        if (isLoginExpired(errorMsg)) {
          setShowQrModal(true);
        }
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || '发布失败';
      setPublishResult({
        success: false,
        platform: selectedPlatform,
        error: errorMsg,
      });

      // 如果是小红书且登录过期，弹出二维码
      if (selectedPlatform === 'xiaohongshu' && isLoginExpired(errorMsg)) {
        setShowQrModal(true);
      }
    } finally {
      setPublishing(false);
    }
  };

  // 登录成功后重试发布
  const handleLoginSuccess = () => {
    showToast('登录成功，可重新发布', 'success');
    setShowQrModal(false);
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
      <h2 className="text-2xl font-bold mb-6">选择发布平台</h2>

      {/* 文案摘要 */}
      <div className="bg-white p-6 rounded-lg shadow mb-6">
        <h3 className="font-semibold mb-2">文案摘要</h3>
        <p className="text-lg font-bold">{script.title}</p>
        <p className="text-gray-600 mt-2 line-clamp-3">{script.body}</p>
      </div>

      {/* 小红书登录 */}
      <div className="bg-white p-6 rounded-lg shadow mb-6">
        <h3 className="font-semibold mb-2">小红书账号</h3>
        <p className="text-sm text-gray-500 mb-3">发布前请确保已登录小红书</p>
        <button
          onClick={() => setShowQrModal(true)}
          className="px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 text-sm"
        >
          📱 扫码登录小红书
        </button>
      </div>

      {/* 平台选择 */}
      <div className="bg-white p-6 rounded-lg shadow mb-6">
        <h3 className="font-semibold mb-4">选择平台</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div
            className={`border-2 rounded-lg p-4 cursor-pointer transition-colors ${
              selectedPlatform === 'xiaohongshu'
                ? 'border-red-500 bg-red-50'
                : 'border-gray-200 hover:border-red-300'
            }`}
            onClick={() => setSelectedPlatform('xiaohongshu')}
          >
            <h4 className="font-semibold text-lg">📕 小红书</h4>
            <p className="text-sm text-gray-600 mt-1">发布笔记到小红书</p>
          </div>

          <div
            className={`border-2 rounded-lg p-4 cursor-pointer transition-colors ${
              selectedPlatform === 'wechat'
                ? 'border-green-500 bg-green-50'
                : 'border-gray-200 hover:border-green-300'
            }`}
            onClick={() => setSelectedPlatform('wechat')}
          >
            <h4 className="font-semibold text-lg">💬 微信公众号</h4>
            <p className="text-sm text-gray-600 mt-1">创建公众号草稿</p>
          </div>
        </div>
      </div>

      {/* 发布按钮 */}
      <div className="flex justify-center mb-6">
        <button
          onClick={handlePublish}
          disabled={!selectedPlatform || publishing}
          className={`px-8 py-3 text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 flex items-center gap-2 ${
            !selectedPlatform || publishing
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700'
          }`}
        >
          {publishing ? (
            <>
              <Loader size={20} className="animate-spin" />
              发布中...
            </>
          ) : (
            <>
              <Send size={20} />
              确认发布
            </>
          )}
        </button>
      </div>

      {/* 发布结果 */}
      {publishResult && (
        <div
          className={`p-6 rounded-lg shadow ${
            publishResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
          }`}
        >
          <div className="flex items-center gap-2 mb-4">
            {publishResult.success ? (
              <CheckCircle className="text-green-600" size={24} />
            ) : (
              <XCircle className="text-red-600" size={24} />
            )}
            <h3 className="font-semibold text-lg">
              {publishResult.success ? '发布成功！' : '发布失败'}
            </h3>
          </div>

          {publishResult.success ? (
            <div>
              {publishResult.note_id && (
                <p className="text-green-700">
                  小红书笔记ID：{publishResult.note_id}
                </p>
              )}
              {publishResult.media_id && (
                <p className="text-green-700">
                  公众号草稿ID：{publishResult.media_id}
                </p>
              )}
            </div>
          ) : (
            <div>
              <p className="text-red-700">{publishResult.error}</p>
              {/* 如果是登录过期，显示重新登录按钮 */}
              {selectedPlatform === 'xiaohongshu' && isLoginExpired(publishResult.error || '') && (
                <button
                  onClick={() => setShowQrModal(true)}
                  className="mt-3 px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600"
                >
                  重新登录小红书
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* 小红书登录二维码弹窗 */}
      <XhsQrCodeModal
        visible={showQrModal}
        onClose={() => setShowQrModal(false)}
        onLoginSuccess={handleLoginSuccess}
      />

      {toast && (
        <div className={`fixed top-4 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-lg text-white text-sm shadow-lg ${toast.type === 'success' ? 'bg-green-500' : 'bg-red-500'}`}>
          {toast.msg}
        </div>
      )}
    </div>
  );
};

export default PublishPage;
