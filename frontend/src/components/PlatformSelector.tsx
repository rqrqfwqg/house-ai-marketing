/*
 * 平台选择组件
 * 功能：选择发布平台（小红书/公众号）
 */
import React from 'react';
import { Platform } from '../types/api';

interface PlatformSelectorProps {
  selectedPlatform: Platform | null;
  onPlatformChange: (platform: Platform) => void;
}

const PlatformSelector: React.FC<PlatformSelectorProps> = ({
  selectedPlatform,
  onPlatformChange,
}) => {
  const platforms = [
    {
      id: 'xiaohongshu' as Platform,
      label: '小红书',
      icon: '📕',
      description: '发布笔记到小红书',
      color: 'red',
    },
    {
      id: 'wechat' as Platform,
      label: '微信公众号',
      icon: '💬',
      description: '创建公众号草稿',
      color: 'green',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {platforms.map((platform) => (
        <div
          key={platform.id}
          className={`border-2 rounded-lg p-4 cursor-pointer transition-colors ${
            selectedPlatform === platform.id
              ? `border-${platform.color}-500 bg-${platform.color}-50`
              : 'border-gray-200 hover:border-gray-300'
          }`}
          onClick={() => onPlatformChange(platform.id)}
        >
          <h4 className="font-semibold text-lg mb-2">
            {platform.icon} {platform.label}
          </h4>
          <p className="text-sm text-gray-600">{platform.description}</p>
        </div>
      ))}
    </div>
  );
};

export default PlatformSelector;
