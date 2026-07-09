<template>
  <div class="preview-page" v-loading="loading">
    <template v-if="script">
      <!-- 预览模式 -->
      <el-card v-if="!editMode" class="section-card" shadow="never">
        <template #header>
          <div class="card-header-flex">
            <span class="card-title">文案预览</span>
            <el-button type="primary" text size="small" @click="toggleEditMode">
              <el-icon><Edit /></el-icon>
              编辑文案
            </el-button>
          </div>
        </template>
        <div class="preview-content">
          <h2 class="preview-title">{{ script.title }}</h2>
          <div class="preview-body" v-html="formattedBody"></div>
          <!-- 特色亮点 -->
          <div v-if="script.highlights && script.highlights.length" class="preview-highlights">
            <div class="highlights-label">✨ 特色亮点</div>
            <div class="highlights-list">
              <span
                v-for="(h, idx) in script.highlights"
                :key="idx"
                class="highlight-item"
              >
                {{ h }}
              </span>
            </div>
          </div>
          <div v-if="script.tags && script.tags.length" class="preview-tags">
            <el-tag
              v-for="tag in script.tags"
              :key="tag"
              size="small"
              style="margin-right: 4px; margin-bottom: 4px"
            >
              {{ tag }}
            </el-tag>
          </div>
        </div>
      </el-card>

      <!-- 编辑模式 -->
      <el-card v-else class="section-card" shadow="never">
        <template #header>
          <div class="card-header-flex">
            <span class="card-title">编辑文案</span>
            <el-button type="info" text size="small" @click="cancelEdit">
              取消
            </el-button>
          </div>
        </template>
        <el-form label-position="top">
          <el-form-item label="标题">
            <el-input v-model="editForm.title" placeholder="请输入标题" />
            <div v-if="titleCount" class="char-counter" :class="{ over: titleCount.overLimit }">
              <template v-if="titleCount.unit === 'byte'">
                剩余 {{ titleCount.remaining }}/{{ Math.floor(titleCount.max / 3) }} 字（字节 {{ titleCount.count }}/{{ titleCount.max }}）
              </template>
              <template v-else>
                {{ titleCount.count }}/{{ titleCount.max }} 字
              </template>
            </div>
            <div v-else class="platform-unbound-tip">
              该文案未绑定平台（旧数据），建议按目标平台重新生成以获得最佳合规
            </div>
          </el-form-item>
          <el-form-item label="正文">
            <el-input
              v-model="editForm.body"
              type="textarea"
              :rows="12"
              placeholder="请输入正文内容"
              resize="vertical"
            />
            <div v-if="bodyCount" class="char-counter" :class="{ over: bodyCount.overLimit }">
              <template v-if="bodyCount.max">
                {{ bodyCount.count }}/{{ bodyCount.max }} 字
              </template>
              <template v-else>
                已输入 {{ bodyCount.count }} 字
              </template>
            </div>
          </el-form-item>
          <el-form-item label="标签">
            <el-input
              v-model="editTagsInput"
              placeholder="多个标签用逗号分隔"
            />
          </el-form-item>
          <el-form-item label="特色亮点">
            <el-input
              v-model="editHighlightsInput"
              placeholder="多个亮点用逗号分隔，如：近地铁,精装修,拎包入住"
            />
          </el-form-item>
        </el-form>
        <div class="edit-actions">
          <el-button type="primary" :loading="saving" @click="handleSave">
            保存
          </el-button>
        </div>
      </el-card>

      <!-- 发布操作 -->
      <div class="publish-area">
        <el-button
          type="success"
          size="large"
          style="width: 100%"
          @click="goPublish"
        >
          <el-icon><Promotion /></el-icon>
          {{ publishButtonText }}
        </el-button>
      </div>
    </template>

    <el-empty v-else-if="!loading" description="未找到文案" :image-size="80" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Edit, Promotion } from '@element-plus/icons-vue'
import { getScript, updateScript } from '@/api/script'
import type { Script, ScriptUpdateRequest } from '@/types'
import { countTitle, countBody, type Platform } from '@/utils/platformRules'

const route = useRoute()
const router = useRouter()

const scriptId = computed(() => Number(route.params.id))

const script = ref<Script | null>(null)
const loading = ref(false)
const editMode = ref(false)
const saving = ref(false)

// 文案绑定的平台（平台优先：生成时写入）
const scriptPlatform = computed<string | null>(
  () => script.value?.platform ?? null
)

// 发布按钮文案随平台变化（微信→发布到微信公众号 / 小红书→发布到小红书；未绑定→选择平台发布）
const publishButtonText = computed(() => {
  if (scriptPlatform.value === 'wechat') return '发布到微信公众号'
  if (scriptPlatform.value === 'xiaohongshu') return '发布到小红书'
  return '选择平台发布'
})

// 编辑态实时约束计数（与 platform_rules 镜像口径一致）
const titleCount = computed(() => {
  const p = scriptPlatform.value
  if (!p) return null
  return countTitle(editForm.title || '', p as Platform)
})
const bodyCount = computed(() => {
  const p = scriptPlatform.value
  if (!p) return null
  return countBody(editForm.body || '', p as Platform)
})

const editForm = reactive<ScriptUpdateRequest>({
  title: '',
  body: '',
  tags: [],
  highlights: [],
})
const editTagsInput = ref('')
const editHighlightsInput = ref('')

const formattedBody = computed(() => {
  if (!script.value?.body) return ''
  // 将换行符转为 <br>，进行简单 HTML 格式化
  const escaped = script.value.body
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  return escaped.replace(/\n/g, '<br>')
})

onMounted(() => {
  if (scriptId.value > 0) {
    loadScript()
  } else {
    ElMessage.warning('缺少文案 ID')
    router.push('/history')
  }
})

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

function toggleEditMode(): void {
  if (!script.value) return
  editForm.title = script.value.title
  editForm.body = script.value.body
  editTagsInput.value = (script.value.tags || []).join(', ')
  editHighlightsInput.value = (script.value.highlights || []).join(', ')
  editMode.value = true
}

function cancelEdit(): void {
  editMode.value = false
}

async function handleSave(): Promise<void> {
  if (!script.value) return
  saving.value = true
  try {
    const tags = editTagsInput.value
      .split(/[,，]/)
      .map((t) => t.trim())
      .filter((t) => t.length > 0)
    editForm.tags = tags

    const highlights = editHighlightsInput.value
      .split(/[,，]/)
      .map((h) => h.trim())
      .filter((h) => h.length > 0)

    const updated = await updateScript(scriptId.value, {
      title: editForm.title,
      body: editForm.body,
      tags,
      highlights,
    })
    script.value = updated
    editMode.value = false
    ElMessage.success('文案保存成功')
  } catch (error: any) {
    const msg =
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      '保存失败，请稍后重试'
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

function goPublish(): void {
  router.push({
    path: '/publish',
    query: { script_id: scriptId.value },
  })
}
</script>

<style scoped>
.preview-page {
  padding-bottom: 20px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.card-header-flex {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.preview-content {
  font-size: 13px;
}

.preview-title {
  font-size: 18px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 14px;
  line-height: 1.4;
}

.preview-body {
  color: #606266;
  line-height: 1.8;
  margin-bottom: 14px;
  word-break: break-word;
}

.preview-tags {
  display: flex;
  flex-wrap: wrap;
}

.preview-highlights {
  margin-bottom: 14px;
}

.highlights-label {
  font-size: 13px;
  font-weight: 600;
  color: #e6a23c;
  margin-bottom: 6px;
}

.highlights-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.highlight-item {
  display: inline-block;
  padding: 2px 8px;
  background: #fdf6ec;
  border: 1px solid #f5dab1;
  border-radius: 4px;
  font-size: 12px;
  color: #e6a23c;
}

.edit-actions {
  margin-top: 12px;
  text-align: right;
}

.char-counter {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.char-counter.over {
  color: #f56c6c;
  font-weight: 600;
}

.platform-unbound-tip {
  font-size: 12px;
  color: #e6a23c;
  margin-top: 4px;
}

.publish-area {
  padding: 12px;
}
</style>
