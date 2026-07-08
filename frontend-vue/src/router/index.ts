/**
 * Vue Router 配置
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/upload' },
  {
    path: '/upload',
    name: 'upload',
    component: () => import('@/pages/UploadPage.vue'),
    meta: { title: '上传房源' },
  },
  {
    path: '/generate',
    name: 'generate',
    component: () => import('@/pages/GeneratePage.vue'),
    meta: { title: '生成文案' },
  },
  {
    path: '/preview/:id',
    name: 'preview',
    component: () => import('@/pages/PreviewPage.vue'),
    meta: { title: '预览文案' },
  },
  {
    path: '/publish',
    name: 'publish',
    component: () => import('@/pages/PublishPage.vue'),
    meta: { title: '发布管理' },
  },
  {
    path: '/history',
    name: 'history',
    component: () => import('@/pages/HistoryPage.vue'),
    meta: { title: '历史记录' },
  },
  {
    path: '/settings/wechat-accounts',
    name: 'wechat-accounts',
    component: () => import('@/pages/WechatAccountPage.vue'),
    meta: { title: '公众号配置' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
