/*
 * 富文本编辑器组件
 * 功能：编辑文案（标题、正文、标签）
 */
import React, { useState } from 'react';
import { EditorContent, useEditor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import Image from '@tiptap/extension-image';
import Link from '@tiptap/extension-link';
import { Script } from '../types/script';

interface ScriptEditorProps {
  script: Script;
  onSave: (updatedScript: Script) => void;
}

const ScriptEditor: React.FC<ScriptEditorProps> = ({ script, onSave }) => {
  const [title, setTitle] = useState(script.title);
  const [tags, setTags] = useState<string[]>(script.tags);
  const [tagInput, setTagInput] = useState('');

  // 初始化Tiptap编辑器
  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({
        placeholder: '开始编写文案正文...',
      }),
      Image,
      Link.configure({
        openOnClick: false,
      }),
    ],
    content: script.body,
  });

  // 保存编辑
  const handleSave = () => {
    if (!editor) return;

    const updatedScript: Script = {
      ...script,
      title,
      body: editor.getHTML(),
      tags,
    };

    onSave(updatedScript);
  };

  // 添加标签
  const handleAddTag = () => {
    if (tagInput.trim() && !tags.includes(tagInput.trim())) {
      setTags([...tags, tagInput.trim()]);
      setTagInput('');
    }
  };

  const handleRemoveTag = (index: number) => {
    const newTags = [...tags];
    newTags.splice(index, 1);
    setTags(newTags);
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      {/* 标题编辑 */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          标题
        </label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* 正文编辑器 */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          正文
        </label>
        <div className="border border-gray-300 rounded-md overflow-hidden">
          {/* 工具栏 */}
          <div className="bg-gray-50 border-b border-gray-300 p-2 flex gap-2">
            <button
              type="button"
              onClick={() => editor?.chain().focus().toggleBold().run()}
              className={`px-2 py-1 rounded ${editor?.isActive('bold') ? 'bg-gray-300' : 'hover:bg-gray-200'}`}
            >
              粗体
            </button>
            <button
              type="button"
              onClick={() => editor?.chain().focus().toggleItalic().run()}
              className={`px-2 py-1 rounded ${editor?.isActive('italic') ? 'bg-gray-300' : 'hover:bg-gray-200'}`}
            >
              斜体
            </button>
            <button
              type="button"
              onClick={() => editor?.chain().focus().toggleHeading({ level: 1 }).run()}
              className={`px-2 py-1 rounded ${editor?.isActive('heading', { level: 1 }) ? 'bg-gray-300' : 'hover:bg-gray-200'}`}
            >
              H1
            </button>
            <button
              type="button"
              onClick={() => editor?.chain().focus().toggleBulletList().run()}
              className={`px-2 py-1 rounded ${editor?.isActive('bulletList') ? 'bg-gray-300' : 'hover:bg-gray-200'}`}
            >
              列表
            </button>
          </div>

          {/* 编辑区域 */}
          <div className="p-4 min-h-[300px]">
            <EditorContent editor={editor} />
          </div>
        </div>
      </div>

      {/* 标签编辑 */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          标签
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
            placeholder="输入标签后按回车添加"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="button"
            onClick={handleAddTag}
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
          >
            添加
          </button>
        </div>
        {tags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {tags.map((tag, index) => (
              <span
                key={index}
                className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
              >
                {tag}
                <button
                  type="button"
                  onClick={() => handleRemoveTag(index)}
                  className="text-blue-600 hover:text-blue-800"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* 保存按钮 */}
      <div className="flex justify-end">
        <button
          type="button"
          onClick={handleSave}
          className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
        >
          保存编辑
        </button>
      </div>
    </div>
  );
};

export default ScriptEditor;
