<template>
  <el-dialog
    :model-value="visible"
    title="小红书扫码登录"
    width="320px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div class="qr-modal-content">
      <!-- 二维码区域 -->
      <div v-loading="loading" class="qr-container">
        <img
          v-if="qrCodeUrl"
          :src="qrCodeUrl"
          alt="小红书登录二维码"
          class="qr-image"
        />
        <div v-else-if="!loading" class="qr-placeholder">
          <el-icon :size="32" color="#c0c4cc"><Picture /></el-icon>
          <span>二维码加载失败</span>
        </div>
      </div>

      <!-- 状态提示 -->
      <div class="status-text">
        <template v-if="countdown > 0 && !loggedIn">
          <span>请使用小红书 App 扫码登录</span>
          <span class="countdown">（{{ countdown }}s 后过期）</span>
        </template>
        <template v-else-if="loggedIn">
          <el-icon color="#67c23a" :size="16"><CircleCheck /></el-icon>
          <span style="color: #67c23a">登录成功！</span>
        </template>
        <template v-else-if="countdown <= 0 && !loggedIn">
          <span style="color: #f56c6c">二维码已过期</span>
        </template>
      </div>

      <!-- 操作按钮 -->
      <div class="qr-actions">
        <el-button
          v-if="!loggedIn && countdown <= 0"
          type="primary"
          size="small"
          @click="fetchQrCode"
        >
          重新获取
        </el-button>
        <el-button
          v-if="!loggedIn && countdown > 0"
          type="text"
          size="small"
          @click="fetchQrCode"
        >
          刷新二维码
        </el-button>
        <el-button v-if="loggedIn" type="success" size="small" @click="handleSuccess">
          完成
        </el-button>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, onBeforeUnmount } from 'vue'
import { Picture, CircleCheck } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getXhsQrCode, getXhsLoginStatus } from '@/api/publish'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  close: []
  loginSuccess: []
}>()

const loading = ref(false)
const qrCodeUrl = ref('')
const countdown = ref(0)
const loggedIn = ref(false)

let pollTimer: ReturnType<typeof setInterval> | null = null
let countdownTimer: ReturnType<typeof setInterval> | null = null

watch(
  () => props.visible,
  (val: boolean) => {
    if (val) {
      loggedIn.value = false
      fetchQrCode()
    } else {
      cleanup()
    }
  }
)

/**
 * 获取二维码
 */
async function fetchQrCode(): Promise<void> {
  loading.value = true
  qrCodeUrl.value = ''
  countdown.value = 0
  cleanup()

  try {
    const res = await getXhsQrCode()
    if (res.success) {
      // 优先使用 qr_code_url，其次使用 qr_code（base64）
      const qrCode = res.data?.qr_code_url || res.data?.qr_code
      if (qrCode) {
        // 如果是 base64 但没有 data: 前缀，加上
        if (qrCode.startsWith('data:image')) {
          qrCodeUrl.value = qrCode
        } else if (qrCode.length > 100 && !qrCode.startsWith('http')) {
          // 可能是纯 base64 字符串
          qrCodeUrl.value = `data:image/png;base64,${qrCode}`
        } else {
          qrCodeUrl.value = qrCode
        }
        countdown.value = res.data?.expire_in || res.data?.exprie_in || 120
        startPolling()
        startCountdown()
      } else {
        ElMessage.error('获取二维码失败')
      }
    } else {
      ElMessage.error('获取二维码失败')
    }
  } catch {
    ElMessage.error('获取二维码失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

/**
 * 开始轮询登录状态
 */
function startPolling(): void {
  pollTimer = setInterval(async () => {
    try {
      const res = await getXhsLoginStatus()
      if (res.logged_in) {
        loggedIn.value = true
        stopPolling()
        ElMessage.success('小红书登录成功')
        emit('loginSuccess')
      }
    } catch {
      // 静默处理轮询错误
    }
  }, 3000)
}

/**
 * 开始倒计时
 */
function startCountdown(): void {
  countdownTimer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      stopCountdown()
      stopPolling()
    }
  }, 1000)
}

function stopPolling(): void {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function stopCountdown(): void {
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
}

function cleanup(): void {
  stopPolling()
  stopCountdown()
}

/**
 * 关闭弹窗
 */
function handleClose(): void {
  cleanup()
  emit('close')
}

/**
 * 登录成功后关闭
 */
function handleSuccess(): void {
  cleanup()
  emit('close')
}

onBeforeUnmount(() => {
  cleanup()
})
</script>

<style scoped>
.qr-modal-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 0;
}

.qr-container {
  width: 200px;
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  overflow: hidden;
}

.qr-image {
  width: 180px;
  height: 180px;
  object-fit: contain;
}

.qr-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #c0c4cc;
  font-size: 13px;
}

.status-text {
  margin-top: 16px;
  font-size: 14px;
  color: #606266;
  display: flex;
  align-items: center;
  gap: 4px;
}

.countdown {
  color: #f56c6c;
  font-size: 12px;
}

.qr-actions {
  margin-top: 16px;
}
</style>
