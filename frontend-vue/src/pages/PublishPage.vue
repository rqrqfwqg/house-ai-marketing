<template>
  <div class="publish-page" v-loading="loading">
    <!-- 文案摘要 -->
    <el-card v-if="script" class="section-card" shadow="never">
      <template #header>
        <span class="card-title">文案摘要</span>
      </template>
      <div class="script-summary">
        <div class="summary-title">{{ script.title }}</div>
        <div class="summary-body">
          {{ script.body.length > 120 ? script.body.slice(0, 120) + '...' : script.body }}
        </div>
        <div v-if="script.tags && script.tags.length" class="summary-tags">
          <el-tag
            v-for="tag in script.tags"
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
    </el-card>

    <!-- 平台选择 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <span class="card-title">选择发布平台</span>
      </template>
      <div class="platform-cards">
        <div
          class="platform-card"
          :class="{ active: selectedPlatform === 'xiaohongshu' }"
          @click="selectedPlatform = 'xiaohongshu'"
        >
          <el-icon :size="24" color="#ff2442">
            <component :is="selectedPlatform === 'xiaohongshu' ? 'CircleCheck' : 'ChatRound'" />
          </el-icon>
          <div class="platform-name">小红书</div>
          <div class="platform-desc">发布到小红书笔记</div>
        </div>
        <div
          class="platform-card"
          :class="{ active: selectedPlatform === 'wechat' }"
          @click="selectedPlatform = 'wechat'"
        >
          <el-icon :size="24" color="#07c160">
            <component :is="selectedPlatform === 'wechat' ? 'CircleCheck' : 'ChatDotSquare'" />
          </el-icon>
          <div class="platform-name">微信公众号</div>
          <div class="platform-desc">创建微信草稿</div>
        </div>
      </div>
    </el-card>

    <!-- 公众号账号选择（仅微信平台） -->
    <el-card v-if="selectedPlatform === 'wechat'" class="section-card" shadow="never">
      <template #header>
        <span class="card-title">选择发布账号</span>
      </template>
      <el-select
        v-model="selectedWechatAccountId"
        placeholder="选择要发布的公众号账号（不选则使用默认账号）"
        style="width: 100%"
        clearable
        :loading="loadingWechatAccounts"
      >
        <el-option
          v-for="acc in wechatAccounts"
          :key="acc.id"
          :label="`${acc.name}（${acc.app_id_masked}）`"
          :value="acc.id"
        />
      </el-select>
      <div v-if="!loadingWechatAccounts && wechatAccounts.length === 0" class="account-hint">
        暂无启用的公众号账号，请前往
        <router-link to="/settings/wechat-accounts" class="link">公众号配置</router-link>
        添加账号。
      </div>
    </el-card>

    <!-- 发布按钮 -->
    <div class="publish-btn-area">
      <el-button
        type="primary"
        size="large"
        style="width: 100%"
        :loading="publishing"
        :disabled="!script"
        @click="handlePublish"
      >
        {{ publishing ? '发布中...' : `发布到${platformLabel}` }}
      </el-button>
      <el-button
        v-if="selectedPlatform === 'xiaohongshu'"
        type="warning"
        plain
        size="default"
        style="width: 100%; margin-top: 8px; margin-left: 0"
        @click="showQrCode = true"
      >
        小红书登录二维码
      </el-button>
    </div>

    <!-- 发布结果 -->
    <el-card v-if="publishResult" class="section-card" shadow="never">
      <el-result
        :icon="publishResult.success ? 'success' : 'error'"
        :title="resultTitle"
        :sub-title="resultSubTitle"
      />

      <!-- 公众号：草稿已上传到草稿箱 -->
      <div v-if="publishResult.success && selectedPlatform === 'wechat' && publishResult.media_id" class="wechat-draft-result">
        <el-alert
          type="success"
          :closable="false"
          show-icon
          title="草稿已上传到公众号后台草稿箱"
          :description="`草稿 ID：${publishResult.media_id}`"
        />
        <div class="action-buttons" style="margin-top: 12px;">
          <el-button type="success" plain @click="openEditor(publishResult.editor_url)">
            前往公众号后台
          </el-button>
        </div>
      </div>

      <!-- 公众号：复制文案备用（content 存在时） -->
      <div v-if="publishResult.success && selectedPlatform === 'wechat' && publishResult.content" class="wechat-actions">
        <div class="content-preview">
          <pre>{{ publishResult.content }}</pre>
        </div>
        <div class="action-buttons">
          <el-button type="primary" @click="copyContent(publishResult.content)">
            复制文案
          </el-button>
          <el-button type="success" plain @click="openEditor(publishResult.editor_url)">
            打开公众号编辑器
          </el-button>
        </div>
      </div>

      <!-- 小红书：显示笔记ID -->
      <div v-if="publishResult.success && selectedPlatform === 'xiaohongshu' && publishResult.note_id" class="xhs-result">
        <el-tag type="success">笔记 ID: {{ publishResult.note_id }}</el-tag>
      </div>
    </el-card>

    <!-- 小红书二维码弹窗 -->
    <XhsQrCodeModal
      :visible="showQrCode"
      @close="showQrCode = false"
      @login-success="handleXhsLoginSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import XhsQrCodeModal from '@/components/XhsQrCodeModal.vue'
import { getScript } from '@/api/script'
import { publish } from '@/api/publish'
import { getWechatAccounts } from '@/api/wechatAccount'
import type { Script, Platform, PublishResponse, WechatAccount } from '@/types'

const route = useRoute()
const router = useRouter()

const scriptId = computed(() => {
  const raw = route.query.script_id
  return raw ? Number(raw) : 0
})

const script = ref<Script | null>(null)
const loading = ref(false)
const publishing = ref(false)
const selectedPlatform = ref<Platform>('xiaohongshu')
const publishResult = ref<PublishResponse | null>(null)
const showQrCode = ref(false)

// 公众号账号下拉
const wechatAccounts = ref<WechatAccount[]>([])
const selectedWechatAccountId = ref<number | undefined>(undefined)
const loadingWechatAccounts = ref(false)

const platformLabel = computed(() => {
  return selectedPlatform.value === 'xiaohongshu' ? '小红书' : '微信公众号'
})

const resultTitle = computed(() => {
  if (!publishResult.value) return ''
  if (publishResult.value.success) {
    if (selectedPlatform.value === 'wechat') {
      return '草稿已上传'
    }
    return '发布成功'
  }
  return '发布失败'
})

const resultSubTitle = computed(() => {
  if (!publishResult.value) return ''
  if (publishResult.value.success) {
    if (publishResult.value.note_id) {
      return `笔记 ID: ${publishResult.value.note_id}`
    }
    if (publishResult.value.media_id) {
      return `草稿 ID: ${publishResult.value.media_id}`
    }
    return '操作成功'
  }
  return publishResult.value.error || '请稍后重试'
})

onMounted(() => {
  if (scriptId.value > 0) {
    loadScript()
  } else {
    ElMessage.warning('缺少文案 ID')
    router.push('/history')
  }
})

// 切换平台时按需加载公众号账号
watch(selectedPlatform, (platform) => {
  if (platform === 'wechat') {
    // 切回小红书时清空选择，避免误带账号
    loadWechatAccounts()
  } else {
    selectedWechatAccountId.value = undefined
  }
})

async function loadWechatAccounts(): Promise<void> {
  loadingWechatAccounts.value = true
  try {
    const res = await getWechatAccounts(true)
    wechatAccounts.value = res.items || []
    if (wechatAccounts.value.length === 0) {
      ElMessage.warning('暂无启用的公众号账号，请前往「公众号配置」添加')
    }
  } catch (error: any) {
    const msg =
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      '获取公众号账号失败'
    ElMessage.warning(`${msg}（请前往「公众号配置」添加账号）`)
    wechatAccounts.value = []
  } finally {
    loadingWechatAccounts.value = false
  }
}

async function loadScript(): Promise<void> {
  loading.value = true
  try {
    script.value = await getScript(scriptId.value)
  } catch {
    ElMessage.error('获取文案失败')
  } finally {
    loading.value = false
  }
}

async function handlePublish(): Promise<void> {
  if (!script.value) return

  publishing.value = true
  publishResult.value = null
  try {
    const payload: { script_id: number; images: string[]; wechat_account_id?: number } = {
      script_id: scriptId.value,
      images: [], // 后端从房源获取图片，此字段由后端处理
    }
    // 仅微信公众号平台随请求发送账号 ID
    if (selectedPlatform.value === 'wechat') {
      payload.wechat_account_id = selectedWechatAccountId.value ?? undefined
    }

    const result = await publish(selectedPlatform.value, payload)
    publishResult.value = result
    if (result.success) {
      ElMessage.success('发布成功！')
    } else {
      ElMessage.error(result.error || '发布失败')
    }
  } catch (error: any) {
    const msg =
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      '发布失败，请稍后重试'
    ElMessage.error(msg)
    publishResult.value = {
      success: false,
      platform: selectedPlatform.value,
      error: msg,
    }
  } finally {
    publishing.value = false
  }
}

function handleXhsLoginSuccess(): void {
  ElMessage.success('小红书已登录，可以发布了')
}

async function copyContent(content: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(content)
    ElMessage.success('文案已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败，请手动选择文本复制')
  }
}

function openEditor(url?: string): void {
  if (url) {
    window.open(url, '_blank')
  }
}
</script>

<style scoped>
.publish-page {
  padding-bottom: 20px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.script-summary {
  font-size: 13px;
}

.summary-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 6px;
}

.summary-body {
  color: #909399;
  line-height: 1.6;
  margin-bottom: 8px;
}

.summary-tags {
  display: flex;
  flex-wrap: wrap;
}

.platform-cards {
  display: flex;
  gap: 12px;
}

.platform-card {
  flex: 1;
  border: 2px solid #e8e8e8;
  border-radius: 8px;
  padding: 16px 8px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.platform-card:hover {
  border-color: #c0d8ff;
}

.platform-card.active {
  border-color: #409eff;
  background-color: #f0f7ff;
}

.platform-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-top: 6px;
}

.platform-desc {
  font-size: 11px;
  color: #909399;
  margin-top: 2px;
}

.account-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
  line-height: 1.5;
}

.link {
  color: #409eff;
  text-decoration: none;
}

.link:hover {
  text-decoration: underline;
}

.publish-btn-area {
  padding: 12px;
}

.wechat-actions {
  margin-top: 16px;
}

.wechat-draft-result {
  margin-top: 16px;
}

.content-preview {
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
  max-height: 300px;
  overflow-y: auto;
}

.content-preview pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.6;
  color: #303133;
  margin: 0;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.xhs-result {
  margin-top: 12px;
  text-align: center;
}
</style>
