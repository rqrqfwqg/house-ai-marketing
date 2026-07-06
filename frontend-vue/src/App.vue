<template>
  <div class="app-container">
    <!-- 顶部导航栏 -->
    <div class="app-header">
      <span class="app-title">AI营销</span>
      <span class="app-subtitle">房屋租赁智能营销系统</span>
    </div>

    <!-- 路由出口 -->
    <div class="page-content">
      <router-view />
    </div>

    <!-- 底部 Tab 导航 -->
    <div class="bottom-nav">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ active: isActive(item.path) }"
      >
        <el-icon :size="22">
          <component :is="item.icon" />
        </el-icon>
        <span class="nav-label">{{ item.label }}</span>
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Upload, Promotion, Clock } from '@element-plus/icons-vue'

const route = useRoute()

const navItems = computed(() => [
  { path: '/upload', label: '上传', icon: Upload },
  { path: '/generate', label: '生成', icon: Promotion },
  { path: '/history', label: '记录', icon: Clock },
])

function isActive(path: string): boolean {
  if (path === '/generate') {
    return route.path === '/generate' || route.path === '/preview' || route.path.startsWith('/preview/')
  }
  if (path === '/history') {
    return route.path === '/history' || route.path === '/publish'
  }
  return route.path === path
}
</script>

<style scoped>
.app-header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  background: linear-gradient(135deg, #409eff, #5b8cff);
  color: #fff;
  flex-shrink: 0;
}

.app-title {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.2;
}

.app-subtitle {
  font-size: 10px;
  opacity: 0.85;
  margin-top: 2px;
}

.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 430px;
  height: 56px;
  display: flex;
  background: #fff;
  border-top: 1px solid #e8e8e8;
  z-index: 1000;
}

.nav-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  color: #999;
  transition: color 0.2s;
}

.nav-item.active {
  color: #409eff;
}

.nav-label {
  font-size: 11px;
  margin-top: 2px;
}
</style>
