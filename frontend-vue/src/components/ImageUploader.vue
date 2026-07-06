<template>
  <div class="image-uploader">
    <!-- 9 格横排 -->
    <div class="image-grid">
      <div
        v-for="index in maxImages"
        :key="index"
        class="image-cell"
        :class="{ 'has-image': previews[index - 1] }"
      >
        <!-- 已上传图片 -->
        <template v-if="previews[index - 1]">
          <img
            :src="previews[index - 1]"
            class="thumb-img"
            alt="房源图片"
            @click="previewImage(index - 1)"
          />
          <div class="delete-btn" @click.stop="removeImage(index - 1)">
            <el-icon :size="10"><Close /></el-icon>
          </div>
        </template>

        <!-- 空位占位 -->
        <template v-else>
          <label class="upload-label" :for="`img-input-${instanceId}`">
            <el-icon :size="14" color="#bbb"><Plus /></el-icon>
          </label>
        </template>
      </div>
    </div>

    <!-- 隐藏的文件输入，统一处理选择 -->
    <input
      :id="`img-input-${instanceId}`"
      ref="fileInputRef"
      type="file"
      accept="image/*"
      multiple
      class="hidden-input"
      @change="handleFileChange"
    />

    <div class="upload-tip">
      已选 {{ files.length }}/{{ maxImages }} 张图片（最多 {{ maxImages }} 张）
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, getCurrentInstance } from 'vue'
import { Plus, Close } from '@element-plus/icons-vue'
import { ElMessage, ElImageViewer } from 'element-plus'
import { h, render } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: File[]
    maxImages?: number
  }>(),
  {
    modelValue: () => [],
    maxImages: 9,
  }
)

const emit = defineEmits<{
  'update:modelValue': [files: File[]]
}>()

const files = ref<File[]>([...props.modelValue])
const previews = ref<string[]>([])
const fileInputRef = ref<HTMLInputElement | null>(null)

// 唯一实例 ID，用于 label-for 关联
const instanceId = computed(() => {
  return `iu-${getCurrentInstance()?.uid ?? Math.random().toString(36).slice(2)}`
})

// 监听外部 modelValue 变化
watch(
  () => props.modelValue,
  (newFiles: File[]) => {
    if (newFiles.length !== files.value.length) {
      files.value = [...newFiles]
      regeneratePreviews()
    }
  },
  { deep: true }
)

/**
 * 重新生成所有预览图（base64）
 */
async function regeneratePreviews(): Promise<void> {
  previews.value = []
  for (const file of files.value) {
    const base64 = await fileToBase64(file)
    previews.value.push(base64)
  }
}

/**
 * 将 File 转为 base64 字符串
 */
function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      resolve(reader.result as string)
    }
    reader.onerror = () => {
      reject(new Error('文件读取失败'))
    }
    reader.readAsDataURL(file)
  })
}

/**
 * 文件选择处理
 */
async function handleFileChange(event: Event): Promise<void> {
  const target = event.target as HTMLInputElement
  const selectedFiles = target.files
  if (!selectedFiles || selectedFiles.length === 0) return

  const newFiles = Array.from(selectedFiles)
  const availableSlots = props.maxImages - files.value.length

  if (newFiles.length > availableSlots) {
    ElMessage.warning(`最多只能上传 ${props.maxImages} 张图片，已自动截取前 ${availableSlots} 张`)
  }

  const filesToAdd = newFiles.slice(0, availableSlots)

  for (const file of filesToAdd) {
    files.value.push(file)
    try {
      const base64 = await fileToBase64(file)
      previews.value.push(base64)
    } catch {
      // 读取失败时跳过该文件
      const idx = files.value.indexOf(file)
      if (idx > -1) files.value.splice(idx, 1)
      ElMessage.error(`图片 "${file.name}" 读取失败`)
    }
  }

  emit('update:modelValue', [...files.value])

  // 重置 input，以便可以重复选择同一文件
  target.value = ''
}

/**
 * 删除指定位置的图片
 */
function removeImage(index: number): void {
  files.value.splice(index, 1)
  previews.value.splice(index, 1)
  emit('update:modelValue', [...files.value])
}

/**
 * 预览大图
 */
function previewImage(index: number): void {
  const viewer = h(ElImageViewer, {
    urlList: previews.value,
    initialIndex: index,
    onClose: () => {
      document.body.removeChild(container)
    },
  })
  const container = document.createElement('div')
  document.body.appendChild(container)
  render(viewer, container)
}

// 初始化时生成预览
if (files.value.length > 0) {
  regeneratePreviews()
}
</script>

<style scoped>
.image-uploader {
  width: 100%;
}

.image-grid {
  display: flex;
  flex-wrap: nowrap;
  gap: 4px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  padding-bottom: 2px;
}

.image-cell {
  flex-shrink: 0;
  width: 38px;
  height: 38px;
  border: 1px dashed #dcdfe6;
  border-radius: 6px;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #fafafa;
  cursor: pointer;
  transition: border-color 0.2s;
}

.image-cell.has-image {
  border: 1px solid #e4e7ed;
}

.thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.delete-btn {
  position: absolute;
  top: 0;
  right: 0;
  width: 14px;
  height: 14px;
  background-color: rgba(0, 0, 0, 0.55);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0 0 0 6px;
  cursor: pointer;
  z-index: 2;
}

.upload-label {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.hidden-input {
  display: none;
}

.upload-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
  line-height: 1.4;
}
</style>
