/*
 * 小红书登录二维码弹窗
 * 功能：展示登录二维码、自动轮询登录状态、超时提示
 */
import React, { useState, useEffect, useRef } from 'react';
import { X } from 'lucide-react';

interface XhsQrCodeModalProps {
  visible: boolean;
  onClose: () => void;
  onLoginSuccess: () => void;
}

const XhsQrCodeModal: React.FC<XhsQrCodeModalProps> = ({
  visible,
  onClose,
  onLoginSuccess,
}) => {
  const [qrCodeUrl, setQrCodeUrl] = useState<string>('');
  const [countdown, setCountdown] = useState(120);
  const [polling, setPolling] = useState(true);
  const timerRef = useRef<number | null>(null);
  const pollRef = useRef<number | null>(null);

  // 本地 toast（替代 antd-mobile 的 Toast）
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null);
  const showToast = (msg: string, type: 'success' | 'error' = 'error') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 2500);
  };

  // 获取二维码
  const fetchQrCode = async () => {
    try {
      const res = await fetch('/api/v1/publish/xhs-qrcode');
      const data = await res.json();
      if (data.success) {
        // qr_code 可能是 base64 或 url
        const code = data.data.qr_code_url || data.data.qr_code;
        setQrCodeUrl(code);
        setCountdown(data.data.exprie_in || 120);
        setPolling(true);
      } else {
        showToast(data.message || '获取二维码失败');
      }
    } catch (err: any) {
      showToast('获取二维码失败：' + err.message);
    }
  };

  // 轮询登录状态
  const startPolling = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = window.setInterval(async () => {
      try {
        const res = await fetch('/api/v1/publish/xhs-login-status');
        const data = await res.json();
        if (data.logged_in) {
          // 登录成功
          if (pollRef.current) clearInterval(pollRef.current);
          setPolling(false);
          showToast('登录成功！', 'success');
          onLoginSuccess();
          onClose();
        }
      } catch {
        // 忽略轮询错误
      }
    }, 2000);
  };

  // 倒计时
  useEffect(() => {
    if (!visible) return;
    fetchQrCode();
  }, [visible]);

  useEffect(() => {
    if (!visible || !polling) return;
    startPolling();
    timerRef.current = window.setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          // 倒计时结束，重新获取二维码
          fetchQrCode();
          return 120;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [visible, polling]);

  // 处理二维码 URL（支持 base64 或普通 URL）
  const renderQrCode = () => {
    if (!qrCodeUrl) return <div className="text-gray-400 text-sm">加载中...</div>;

    // 如果是 base64 格式
    if (qrCodeUrl.startsWith('data:')) {
      return <img src={qrCodeUrl} alt="登录二维码" className="w-48 h-48 mx-auto" />;
    }
    // 如果是 URL
    if (qrCodeUrl.startsWith('http')) {
      return <img src={qrCodeUrl} alt="登录二维码" className="w-48 h-48 mx-auto" />;
    }
    // 否则当作 base64 处理
    return <img src={`data:image/png;base64,${qrCodeUrl}`} alt="登录二维码" className="w-48 h-48 mx-auto" />;
  };

  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-lg max-w-sm w-full mx-4 p-4">
        <div className="text-center">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-bold">小红书登录</h3>
            <button onClick={onClose} className="p-1">
              <X size={20} />
            </button>
          </div>

          <p className="text-sm text-gray-600 mb-4">
            请使用小红书 App 扫描下方二维码登录
          </p>

          <div className="bg-white p-4 rounded-lg inline-block mb-4">
            {renderQrCode()}
          </div>

          <p className="text-xs text-gray-500 mb-2">
            二维码有效期：{countdown} 秒
          </p>

          <button
            className="text-sm text-blue-500 underline"
            onClick={() => {
              fetchQrCode();
              setCountdown(120);
            }}
          >
            刷新二维码
          </button>
        </div>
      </div>

      {toast && (
        <div className={`fixed top-4 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-lg text-white text-sm shadow-lg ${toast.type === 'success' ? 'bg-green-500' : 'bg-red-500'}`}>
          {toast.msg}
        </div>
      )}
    </div>
  );
};

export default XhsQrCodeModal;
