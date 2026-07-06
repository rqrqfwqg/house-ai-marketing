/*
 * 发布按钮组件
 * 功能：执行发布、显示状态反馈
 */
import React from 'react';
import { Loader, CheckCircle, XCircle } from 'lucide-react';
import { PublishResponse } from '../types/api';

interface PublishButtonProps {
  onClick: () => void;
  loading: boolean;
  result: PublishResponse | null;
  disabled: boolean;
}

const PublishButton: React.FC<PublishButtonProps> = ({
  onClick,
  loading,
  result,
  disabled,
}) => {
  return (
    <div>
      {/* 发布按钮 */}
      <button
        onClick={onClick}
        disabled={disabled || loading}
        className={`px-8 py-3 text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 flex items-center gap-2 ${
          disabled || loading
            ? 'bg-gray-400 cursor-not-allowed'
            : 'bg-blue-600 hover:bg-blue-700'
        }`}
      >
        {loading ? (
          <>
            <Loader size={20} className="animate-spin" />
            发布中...
          </>
        ) : (
          '确认发布'
        )}
      </button>

      {/* 发布结果反馈 */}
      {result && (
        <div
          className={`mt-4 p-4 rounded-md ${
            result.success
              ? 'bg-green-50 border border-green-200'
              : 'bg-red-50 border border-red-200'
          }`}
        >
          <div className="flex items-center gap-2">
            {result.success ? (
              <CheckCircle className="text-green-600" size={20} />
            ) : (
              <XCircle className="text-red-600" size={20} />
            )}
            <p className={result.success ? 'text-green-700' : 'text-red-700'}>
              {result.success ? '发布成功！' : `发布失败：${result.error}`}
            </p>
          </div>

          {result.success && result.note_id && (
            <p className="mt-2 text-sm text-green-600">
              小红书笔记ID：{result.note_id}
            </p>
          )}

          {result.success && result.media_id && (
            <p className="mt-2 text-sm text-green-600">
              公众号草稿ID：{result.media_id}
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default PublishButton;
