<template>
  <div class="upload-page">
    <!-- 图片上传区 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <span class="card-title">房源图片</span>
      </template>
      <ImageUploader v-model="selectedFiles" :max-images="9" />
    </el-card>

    <!-- 房源信息表单 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <span class="card-title">房源信息</span>
      </template>
      <el-form
        ref="formRef"
        :model="houseForm"
        label-position="top"
        size="default"
      >
        <el-form-item label="标题">
          <el-input
            v-model="houseForm.title"
            placeholder="如：南向两居室 精装修 拎包入住"
            clearable
          />
        </el-form-item>

        <el-form-item label="地址">
          <el-input
            v-model="houseForm.address"
            placeholder="如：朝阳区望京SOHO附近"
            clearable
          />
        </el-form-item>

        <div class="form-row">
          <el-form-item label="月租金（元）" class="form-row-item">
            <el-input-number
              v-model="houseForm.rent"
              :min="0"
              :step="100"
              controls-position="right"
              style="width: 100%"
              placeholder="如：5000"
            />
          </el-form-item>

          <el-form-item label="面积（㎡）" class="form-row-item">
            <el-input-number
              v-model="houseForm.area"
              :min="0"
              :step="1"
              :precision="1"
              controls-position="right"
              style="width: 100%"
              placeholder="如：80"
            />
          </el-form-item>
        </div>

        <div class="form-row">
          <el-form-item label="户型" class="form-row-item">
            <el-input
              v-model="houseForm.rooms"
              placeholder="如：2室1厅1卫"
              clearable
            />
          </el-form-item>

          <el-form-item label="楼层" class="form-row-item">
            <el-input
              v-model="houseForm.floor"
              placeholder="如：中楼层/6层"
              clearable
            />
          </el-form-item>
        </div>

        <el-form-item label="标签">
          <el-input
            v-model="tagsInput"
            placeholder="多个标签用逗号分隔，如：近地铁,精装修,拎包入住"
            clearable
          />
        </el-form-item>

        <el-form-item label="特色亮点">
          <el-input
            v-model="highlightsInput"
            placeholder="多个特色用逗号分隔，如：近地铁,南北通透,精装修"
            clearable
          />
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 提交按钮 -->
    <div class="submit-area">
      <el-button
        type="primary"
        size="large"
        style="width: 100%"
        :loading="submitting"
        @click="handleSubmit"
      >
        上传房源
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance } from 'element-plus'
import ImageUploader from '@/components/ImageUploader.vue'
import { uploadHouse } from '@/api/house'
import type { HouseCreate } from '@/types'

const router = useRouter()
const formRef = ref<FormInstance>()
const submitting = ref(false)

const selectedFiles = ref<File[]>([])
const tagsInput = ref('')
const highlightsInput = ref('')

const houseForm = reactive<HouseCreate>({
  title: '',
  address: '',
  rent: undefined,
  rooms: '',
  area: undefined,
  floor: '',
  tags: [],
  highlights: [],
})

/**
 * 提交上传
 */
async function handleSubmit(): Promise<void> {
  if (selectedFiles.value.length === 0) {
    ElMessage.warning('请至少上传一张房源图片')
    return
  }

  // 组装 tags
  const tags = tagsInput.value
    .split(/[,，]/)
    .map((t) => t.trim())
    .filter((t) => t.length > 0)
  houseForm.tags = tags

  // 组装 highlights
  const highlights = highlightsInput.value
    .split(/[,，]/)
    .map((t) => t.trim())
    .filter((t) => t.length > 0)
  houseForm.highlights = highlights

  submitting.value = true
  try {
    const res = await uploadHouse(selectedFiles.value, { ...houseForm })
    ElMessage.success('房源上传成功！')
    // 跳转到生成文案页面
    router.push({
      path: '/generate',
      query: { house_id: res.id },
    })
  } catch (error: any) {
    const msg =
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      '房源上传失败，请稍后重试'
    ElMessage.error(msg)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.upload-page {
  padding-bottom: 20px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.form-row {
  display: flex;
  gap: 12px;
}

.form-row-item {
  flex: 1;
}

.submit-area {
  padding: 12px;
}
</style>
