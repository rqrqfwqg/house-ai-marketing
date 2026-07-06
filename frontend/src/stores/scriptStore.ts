/*
 * 文案状态管理（Zustand）
 * 管理：生成结果、编辑内容、加载状态
 */
import { create } from 'zustand';
import { Script } from '../types/script';

interface ScriptStore {
  // 状态
  currentScript: Script | null;
  generatedScripts: Script[];
  loading: boolean;
  error: string | null;

  // 操作方法
  setCurrentScript: (script: Script | null) => void;
  addGeneratedScript: (script: Script) => void;
  updateScript: (updatedScript: Script) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const useScriptStore = create<ScriptStore>((set) => ({
  // 初始状态
  currentScript: null,
  generatedScripts: [],
  loading: false,
  error: null,

  // 操作方法实现
  setCurrentScript: (script) => set({ currentScript: script }),

  addGeneratedScript: (script) =>
    set((state) => ({
      generatedScripts: [...state.generatedScripts, script],
      currentScript: script,
    })),

  updateScript: (updatedScript) =>
    set((state) => ({
      currentScript: updatedScript,
      generatedScripts: state.generatedScripts.map((s) =>
        s.id === updatedScript.id ? updatedScript : s
      ),
    })),

  setLoading: (loading) => set({ loading }),

  setError: (error) => set({ error }),

  reset: () =>
    set({
      currentScript: null,
      generatedScripts: [],
      loading: false,
      error: null,
    }),
}));

export default useScriptStore;
