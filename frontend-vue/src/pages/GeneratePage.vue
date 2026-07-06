<template>
  <div class="generate-page">
    <!-- 房源信息摘要 -->
    <el-card class="section-card" shadow="never" v-loading="loadingHouse">
      <template #header>
        <span class="card-title">房源信息</span>
      </template>
      <div v-if="house" class="house-summary">
        <div class="house-title">{{ house.title || '未命名房源' }}</div>
        <div class="house-info">
          <span v-if="house.address">{{ house.address }}</span>
          <span v-if="house.rooms"> · {{ house.rooms }}</span>
          <span v-if="house.area"> · {{ house.area }}㎡</span>
          <span v-if="house.rent"> · ¥{{ house.rent }}/月</span>
        </div>
        <div v-if="house.tags && house.tags.length" class="house-tags">
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
        <div v-if="house.highlights && house.highlights.length" class="house-highlights">
          <span
            v-for="(h, idx) in house.highlights"
            :key="idx"
            class="house-highlight-item"
          >
            {{ h }}
          </span>
        </div>
      </div>
      <el-empty v-else description="未找到房源信息" :image-size="60" />
    </el-card>

    <!-- 风格选择 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <span class="card-title">选择文案风格</span>
      </template>
      <div class="style-cards">
        <div
          v-for="(style, key) in TEMPLATE_STYLES"
          :key="key"
          class="style-card"
          :class="{ active: selectedStyle === key }"
          @click="selectedStyle = key"
        >
          <el-icon :size="20" class="style-icon">
            <component :is="styleIcons[key]" />
          </el-icon>
          <div class="style-label">{{ style.label }}</div>
          <div class="style-desc">{{ style.description }}</div>
          <el-icon v-if="selectedStyle === key" class="check-icon" color="#409eff" :size="16">
            <CircleCheck />
          </el-icon>
        </div>
      </div>
    </el-card>

    <!-- 生成按钮 -->
    <div class="generate-btn-area">
      <el-button
        type="primary"
        size="large"
        style="width: 100%"
        :loading="generating"
        :disabled="!house"
        @click="handleGenerate"
      >
        {{ generating ? '正在生成文案...' : '生成文案' }}
      </el-button>
    </div>

    <!-- 生成结果 -->
    <el-card v-if="script" class="section-card" shadow="never">
      <template #header>
        <span class="card-title">生成结果</span>
      </template>
      <div class="script-result">
        <h3 class="script-title">{{ script.title }}</h3>
        <div class="script-body">
          <p
            v-for="(line, idx) in scriptBodyLines"
            :key="idx"
            class="script-line"
          >
            {{ line }}
          </p>
        </div>
        <!-- 特色亮点 -->
        <div v-if="script.highlights && script.highlights.length" class="script-highlights">
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
        <div v-if="script.tags && script.tags.length" class="script-tags">
          <el-tag
            v-for="tag in script.tags"
            :key="tag"
            size="small"
            style="margin-right: 4px; margin-bottom: 4px"
          >
            {{ tag }}
          </el-tag>
        </div>
        <div class="script-actions">
          <el-button type="primary" plain @click="goPreview">
            预览并编辑
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheck, Star, Coffee, MagicStick } from '@element-plus/icons-vue'
import { getHouse } from '@/api/house'
import { generateScript } from '@/api/script'
import { TEMPLATE_STYLES, type House, type Script, type TemplateStyle } from '@/types'

const route = useRoute()
const router = useRouter()

const houseId = computed(() => {
  const raw = route.query.house_id
  return raw ? Number(raw) : 0
})

const house = ref<House | null>(null)
const script = ref<Script | null>(null)
const loadingHouse = ref(false)
const generating = ref(false)
const selectedStyle = ref<TemplateStyle>('professional')

const styleIcons: Record<TemplateStyle, any> = {
  professional: Star,
  friendly: Coffee,
  urgent: MagicStick,
}

const scriptBodyLines = computed(() => {
  if (!script.value?.body) return []
  return script.value.body.split('\n').filter((l) => l.trim().length > 0)
})

onMounted(() => {
  if (houseId.value > 0) {
    loadHouse()
  } else {
    ElMessage.warning('缺少房源 ID，请先上传房源')
    router.push('/upload')
  }
})

async function loadHouse(): Promise<void> {
  loadingHouse.value = true
  try {
    house.value = await getHouse(houseId.value)
  } catch {
    ElMessage.error('获取房源信息失败')
  } finally {
    loadingHouse.value = false
  }
}

async function handleGenerate(): Promise<void> {
  if (!houseId.value) return
  generating.value = true
  script.value = null
  try {
    const result = await generateScript({
      house_id: houseId.value,
      template_style: selectedStyle.value,
    })
    script.value = result
    ElMessage.success('文案生成成功！')
  } catch (error: any) {
    const msg =
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      '文案生成失败，请稍后重试'
    ElMessage.error(msg)
  } finally {
    generating.value = false
  }
}

function goPreview(): void {
  if (script.value) {
    router.push(`/preview/${script.value.id}`)
  }
}
</script>

<style scoped>
.generate-page {
  padding-bottom: 20px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.house-summary {
  font-size: 13px;
}

.house-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 6px;
}

.house-info {
  color: #909399;
  line-height: 1.6;
  margin-bottom: 8px;
}

.house-tags {
  display: flex;
  flex-wrap: wrap;
}

.house-highlights {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.house-highlight-item {
  display: inline-block;
  padding: 2px 8px;
  background: #fdf6ec;
  border: 1px solid #f5dab1;
  border-radius: 4px;
  font-size: 12px;
  color: #e6a23c;
}

.style-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.style-card {
  position: relative;
  border: 2px solid #e8e8e8;
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.style-card:hover {
  border-color: #c0d8ff;
}

.style-card.active {
  border-color: #409eff;
  background-color: #f0f7ff;
}

.style-icon {
  margin-bottom: 4px;
}

.style-label {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.style-desc {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.check-icon {
  position: absolute;
  top: 12px;
  right: 12px;
}

.generate-btn-area {
  padding: 12px;
}

.script-result {
  font-size: 13px;
}

.script-title {
  font-size: 16px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 10px;
}

.script-body {
  line-height: 1.8;
  color: #606266;
  margin-bottom: 10px;
}

.script-line {
  margin-bottom: 4px;
}

.script-tags {
  display: flex;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.script-highlights {
  margin-bottom: 10px;
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

.script-actions {
  margin-top: 8px;
}
</style>
