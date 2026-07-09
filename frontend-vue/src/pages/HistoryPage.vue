<template>
  <div class="history-page" v-loading="loading">
    <!-- 空状态 -->
    <el-empty
      v-if="!loading && houses.length === 0"
      description="还没有上传过房源"
      :image-size="100"
    >
      <el-button type="primary" @click="router.push('/upload')">去上传房源</el-button>
    </el-empty>

    <!-- 房源列表 -->
    <template v-else>
      <el-card
        v-for="house in houses"
        :key="house.id"
        class="section-card"
        shadow="never"
      >
        <template #header>
          <div class="house-card-header">
            <div class="house-info-block">
              <span class="house-name">{{ house.title || `房源 #${house.id}` }}</span>
              <span class="house-meta">
                <span v-if="house.rent">¥{{ house.rent }}/月</span>
                <span v-if="house.area"> · {{ house.area }}㎡</span>
                <span v-if="house.rooms"> · {{ house.rooms }}</span>
              </span>
            </div>
            <el-popconfirm
              title="确定删除该房源及其关联数据吗？"
              confirm-button-text="删除"
              cancel-button-text="取消"
              @confirm="handleDeleteHouse(house.id)"
            >
              <template #reference>
                <el-button text type="danger" size="small">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-popconfirm>
          </div>
        </template>

        <div class="house-card-body">
          <!-- 房源信息 -->
          <div class="house-detail">
            <div v-if="house.address" class="detail-row">
              <el-icon color="#909399" :size="13"><Location /></el-icon>
              <span>{{ house.address }}</span>
            </div>
            <div v-if="house.floor" class="detail-row">
              <el-icon color="#909399" :size="13"><OfficeBuilding /></el-icon>
              <span>{{ house.floor }}</span>
            </div>
            <div v-if="house.tags && house.tags.length" class="detail-tags">
              <el-tag
                v-for="tag in house.tags"
                :key="tag"
                size="small"
                type="info"
                effect="plain"
                style="margin-right: 4px; margin-bottom: 4px"
              >
                {{ tag }}
              </el-tag>
            </div>
          </div>

          <!-- 图片预览（横排小图） -->
          <div v-if="house.images && house.images.length" class="image-row">
            <el-image
              v-for="(img, idx) in house.images"
              :key="idx"
              :src="resolveImageUrl(img)"
              fit="cover"
              class="house-thumb"
              :preview-src-list="house.images.map((i) => resolveImageUrl(i))"
              :initial-index="idx"
              preview-teleported
            />
          </div>

          <!-- 文案列表 -->
          <div class="scripts-section">
            <div class="section-label">文案 ({{ houseScripts(house.id).length }})</div>
            <div v-if="houseScripts(house.id).length === 0" class="empty-hint">
              暂无文案
            </div>
            <div
              v-for="sc in houseScripts(house.id)"
              :key="sc.id"
              class="script-item"
              @click="router.push(`/preview/${sc.id}`)"
            >
              <div class="script-item-title">{{ sc.title }}</div>
              <div class="script-item-meta">
                <el-tag size="small" type="info" effect="plain">
                  {{ styleLabel(sc.template_style) }}
                </el-tag>
                <el-tag
                  v-if="sc.platform"
                  size="small"
                  type="success"
                  effect="plain"
                >
                  {{ platformLabel(sc.platform) }}
                </el-tag>
                <el-tag v-else size="small" type="warning" effect="plain">
                  未绑定平台
                </el-tag>
                <span class="script-date">{{ formatDate(sc.created_at) }}</span>
              </div>
            </div>
          </div>

          <!-- 发布记录 -->
          <div class="publish-section">
            <div class="section-label">发布记录 ({{ housePublishLogs(house.id).length }})</div>
            <div v-if="housePublishLogs(house.id).length === 0" class="empty-hint">
              暂无发布记录
            </div>
            <div
              v-for="log in housePublishLogs(house.id)"
              :key="log.id"
              class="publish-log-item"
            >
              <el-tag :type="publishStatusType(log.status)" size="small">
                {{ publishStatusLabel(log.status) }}
              </el-tag>
              <span class="log-platform">{{ platformLabel(log.platform) }}</span>
              <span v-if="log.error_msg" class="log-error">{{ log.error_msg }}</span>
              <span class="log-date">{{ formatDate(log.created_at) }}</span>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="house-actions">
            <el-button
              type="primary"
              size="small"
              plain
              @click="router.push({ path: '/generate', query: { house_id: house.id } })"
            >
              生成文案
            </el-button>
            <el-button
              v-if="houseScripts(house.id).length > 0"
              type="info"
              size="small"
              plain
              @click="router.push(`/preview/${houseScripts(house.id)[0].id}`)"
            >
              查看文案
            </el-button>
          </div>
        </div>
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Delete, Location, OfficeBuilding } from '@element-plus/icons-vue'
import { getHouses, deleteHouse } from '@/api/house'
import { getScripts } from '@/api/script'
import { getPublishLogs } from '@/api/publish'
import type { House, Script, PublishLog, TemplateStyle } from '@/types'
import { TEMPLATE_STYLES } from '@/types'
import { resolveImageUrl } from '@/utils/imageUrl'

const router = useRouter()

const loading = ref(false)
const houses = ref<House[]>([])
const allScripts = ref<Script[]>([])
const allPublishLogs = ref<PublishLog[]>([])

onMounted(() => {
  loadData()
})

async function loadData(): Promise<void> {
  loading.value = true
  try {
    // 加载房源
    const houseRes = await getHouses(0, 100)
    houses.value = houseRes.items || []

    // 加载所有文案
    const scriptRes = await getScripts(undefined, 0, 500)
    allScripts.value = scriptRes.items || []

    // 加载发布记录
    allPublishLogs.value = await getPublishLogs()
  } catch (error: any) {
    const msg =
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      '加载数据失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

/**
 * 获取指定房源的文案列表
 */
function houseScripts(houseId: number): Script[] {
  return allScripts.value.filter((s) => s.house_id === houseId)
}

/**
 * 获取指定房源的发布记录
 */
function housePublishLogs(houseId: number): PublishLog[] {
  return allPublishLogs.value.filter((l) => l.house_id === houseId)
}

function styleLabel(style?: string): string {
  if (!style) return '默认'
  return TEMPLATE_STYLES[style as TemplateStyle]?.label || style
}

function platformLabel(platform: string): string {
  const map: Record<string, string> = {
    xiaohongshu: '小红书',
    wechat: '微信公众号',
  }
  return map[platform] || platform
}

function publishStatusLabel(status: string): string {
  const map: Record<string, string> = {
    pending: '待发布',
    success: '成功',
    failed: '失败',
    draft_created: '草稿已创建',
  }
  return map[status] || status
}

function publishStatusType(status: string): 'success' | 'danger' | 'warning' | 'info' {
  const map: Record<string, 'success' | 'danger' | 'warning' | 'info'> = {
    pending: 'warning',
    success: 'success',
    failed: 'danger',
    draft_created: 'info',
  }
  return map[status] || 'info'
}

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hours = String(d.getHours()).padStart(2, '0')
  const mins = String(d.getMinutes()).padStart(2, '0')
  return `${month}-${day} ${hours}:${mins}`
}

async function handleDeleteHouse(id: number): Promise<void> {
  try {
    await deleteHouse(id)
    ElMessage.success('删除成功')
    // 从列表中移除
    houses.value = houses.value.filter((h) => h.id !== id)
  } catch (error: any) {
    const msg =
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      '删除失败'
    ElMessage.error(msg)
  }
}
</script>

<style scoped>
.history-page {
  padding-bottom: 20px;
}

.house-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.house-info-block {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.house-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.house-meta {
  font-size: 12px;
  color: #909399;
}

.house-card-body {
  font-size: 13px;
}

.house-detail {
  margin-bottom: 10px;
}

.detail-row {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #909399;
  margin-bottom: 4px;
  font-size: 12px;
}

.detail-tags {
  display: flex;
  flex-wrap: wrap;
  margin-top: 4px;
}

.image-row {
  display: flex;
  gap: 4px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  margin-bottom: 10px;
  padding-bottom: 2px;
}

.house-thumb {
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  border-radius: 4px;
  border: 1px solid #e8e8e8;
  cursor: pointer;
}

.scripts-section,
.publish-section {
  margin-bottom: 10px;
}

.section-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
  font-weight: 500;
}

.empty-hint {
  font-size: 12px;
  color: #c0c4cc;
  padding: 4px 0;
}

.script-item {
  padding: 8px;
  background-color: #f9f9f9;
  border-radius: 6px;
  margin-bottom: 6px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.script-item:hover {
  background-color: #f0f7ff;
}

.script-item-title {
  font-size: 13px;
  color: #303133;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.script-item-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
}

.script-date {
  font-size: 11px;
  color: #c0c4cc;
}

.publish-log-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  background-color: #f9f9f9;
  border-radius: 6px;
  margin-bottom: 4px;
  font-size: 12px;
}

.log-platform {
  color: #606266;
}

.log-error {
  color: #f56c6c;
  font-size: 11px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.log-date {
  font-size: 11px;
  color: #c0c4cc;
  margin-left: auto;
}

.house-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}
</style>
