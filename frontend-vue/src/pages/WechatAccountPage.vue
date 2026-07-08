<template>
  <div class="wechat-account-page" v-loading="loading">
    <!-- 顶部操作区 -->
    <div class="page-toolbar">
      <span class="page-title">公众号配置</span>
      <el-button type="primary" size="small" @click="openCreate">
        <el-icon><Plus /></el-icon>
        <span>新增账号</span>
      </el-button>
    </div>

    <!-- 空状态 -->
    <el-empty
      v-if="!loading && accounts.length === 0"
      description="还没有配置公众号账号"
      :image-size="90"
    >
      <el-button type="primary" @click="openCreate">添加第一个账号</el-button>
    </el-empty>

    <!-- 账号列表 -->
    <el-card v-else class="section-card" shadow="never">
      <div class="table-scroll">
        <el-table :data="accounts" style="width: 100%" :border="false" size="small">
          <el-table-column prop="name" label="名称" min-width="110">
            <template #default="{ row }">
              <span class="cell-name">{{ row.name }}</span>
            </template>
          </el-table-column>

          <el-table-column label="AppID" min-width="140">
            <template #default="{ row }">
              <span class="cell-mono">{{ row.app_id_masked }}</span>
            </template>
          </el-table-column>

          <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="cell-muted">{{ row.remark || '-' }}</span>
            </template>
          </el-table-column>

          <el-table-column label="是否启用" min-width="80" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.is_active" size="small" type="success" effect="light">启用</el-tag>
              <el-tag v-else size="small" type="info" effect="light">停用</el-tag>
            </template>
          </el-table-column>

          <el-table-column label="是否默认" min-width="80" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.is_default" size="small" type="success" effect="plain">默认</el-tag>
              <span v-else class="cell-muted">-</span>
            </template>
          </el-table-column>

          <el-table-column label="创建时间" min-width="130">
            <template #default="{ row }">
              <span class="cell-muted">{{ formatDate(row.created_at) }}</span>
            </template>
          </el-table-column>

          <el-table-column label="操作" min-width="200" fixed="right">
            <template #default="{ row }">
              <div class="row-actions">
                <el-button size="small" @click="openEdit(row)">编辑</el-button>
                <el-button size="small" type="success" plain @click="handleTest(row)">
                  测试
                </el-button>
                <el-popconfirm
                  :title="`确定删除「${row.name}」吗？`"
                  confirm-button-text="删除"
                  cancel-button-text="取消"
                  @confirm="handleDelete(row)"
                >
                  <template #reference>
                    <el-button size="small" type="danger" plain>删除</el-button>
                  </template>
                </el-popconfirm>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- 新增 / 编辑 弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新增公众号账号' : '编辑公众号账号'"
      width="92%"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="92px"
        label-position="top"
      >
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="如：XX房产主号" maxlength="50" />
        </el-form-item>

        <el-form-item label="AppID" prop="app_id">
          <el-input
            v-model="form.app_id"
            placeholder="以 wx 开头，如 wx1234567890abcdef"
            :disabled="dialogMode === 'edit'"
          />
          <div v-if="dialogMode === 'edit'" class="form-hint">
            当前 AppID：{{ editingMaskedAppId }}（编辑时不可修改，如需更换请删除重建）
          </div>
        </el-form-item>

        <el-form-item :label="dialogMode === 'create' ? 'AppSecret' : 'AppSecret（留空不修改）'" prop="app_secret">
          <el-input
            v-model="form.app_secret"
            type="password"
            show-password
            placeholder="输入后仅经 API 发送，前端不存储"
            autocomplete="new-password"
          />
        </el-form-item>

        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" placeholder="可选，便于区分账号" maxlength="100" />
        </el-form-item>

        <el-form-item label="是否启用" prop="is_active">
          <el-switch v-model="form.is_active" />
        </el-form-item>

        <el-form-item label="是否默认" prop="is_default">
          <el-switch v-model="form.is_default" />
          <div class="form-hint">设为默认后，发布未指定账号时将使用该账号（全局仅一个默认）。</div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  getWechatAccounts,
  createWechatAccount,
  updateWechatAccount,
  deleteWechatAccount,
  testWechatAccount,
} from '@/api/wechatAccount'
import type {
  WechatAccount,
  WechatAccountCreate,
  WechatAccountUpdate,
} from '@/types'

// ==================== 状态 ====================
const loading = ref(false)
const submitting = ref(false)
const accounts = ref<WechatAccount[]>([])

const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const editingId = ref<number | undefined>(undefined)
const editingMaskedAppId = ref<string>('')

// ==================== 表单 ====================
const formRef = ref<FormInstance>()
const form = reactive({
  name: '',
  app_id: '',
  app_secret: '',
  remark: '',
  is_active: true,
  is_default: false,
})

// 表单校验：新增时 name/app_id/app_secret 必填；编辑时 app_secret 可空（表示不修改）
const formRules = computed<FormRules>(() => ({
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  app_id: [
    {
      required: dialogMode.value === 'create',
      message: '请输入 AppID',
      trigger: 'blur',
    },
    {
      validator: (_rule, value: string, callback) => {
        if (value && !value.startsWith('wx')) {
          callback(new Error('AppID 需以 wx 开头'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
  app_secret: [
    {
      required: dialogMode.value === 'create',
      message: '请输入 AppSecret',
      trigger: 'blur',
    },
  ],
}))

// ==================== 数据加载 ====================
onMounted(() => {
  loadAccounts()
})

async function loadAccounts(): Promise<void> {
  loading.value = true
  try {
    const res = await getWechatAccounts()
    accounts.value = res.items || []
  } catch (error: any) {
    const msg =
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      '加载账号列表失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

// ==================== 弹窗控制 ====================
function openCreate(): void {
  dialogMode.value = 'create'
  editingId.value = undefined
  editingMaskedAppId.value = ''
  resetForm()
  dialogVisible.value = true
}

function openEdit(acc: WechatAccount): void {
  dialogMode.value = 'edit'
  editingId.value = acc.id
  editingMaskedAppId.value = acc.app_id_masked
  form.name = acc.name
  form.app_id = ''
  form.app_secret = ''
  form.remark = acc.remark || ''
  form.is_active = acc.is_active
  form.is_default = acc.is_default
  dialogVisible.value = true
}

function resetForm(): void {
  formRef.value?.clearValidate()
  form.name = ''
  form.app_id = ''
  form.app_secret = ''
  form.remark = ''
  form.is_active = true
  form.is_default = false
}

// ==================== 提交（新增 / 编辑） ====================
async function handleSubmit(): Promise<void> {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    if (dialogMode.value === 'create') {
      const payload: WechatAccountCreate = {
        name: form.name.trim(),
        app_id: form.app_id.trim(),
        app_secret: form.app_secret,
        remark: form.remark.trim() || undefined,
        is_active: form.is_active,
        is_default: form.is_default,
      }
      await createWechatAccount(payload)
      ElMessage.success('账号已添加')
    } else {
      const payload: WechatAccountUpdate = {
        name: form.name.trim(),
        remark: form.remark.trim() || undefined,
        is_active: form.is_active,
        is_default: form.is_default,
      }
      // 仅在填写时发送 app_id / app_secret（留空表示不修改）
      if (form.app_id.trim()) payload.app_id = form.app_id.trim()
      if (form.app_secret) payload.app_secret = form.app_secret
      await updateWechatAccount(editingId.value as number, payload)
      ElMessage.success('账号已更新')
    }
    dialogVisible.value = false
    await loadAccounts()
  } catch (error: any) {
    const msg =
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      '保存失败'
    ElMessage.error(msg)
  } finally {
    submitting.value = false
  }
}

// ==================== 删除 ====================
async function handleDelete(acc: WechatAccount): Promise<void> {
  try {
    await deleteWechatAccount(acc.id)
    ElMessage.success('账号已删除')
    await loadAccounts()
  } catch (error: any) {
    const msg =
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      '删除失败'
    ElMessage.error(msg)
  }
}

// ==================== 测试连通 ====================
async function handleTest(acc: WechatAccount): Promise<void> {
  try {
    const res = await testWechatAccount(acc.id)
    if (res.success) {
      ElMessage.success(res.message || '连接成功')
    } else {
      ElMessage.warning(res.message || '连接失败')
    }
  } catch (error: any) {
    const msg =
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      '测试失败'
    ElMessage.error(msg)
  }
}

// ==================== 工具 ====================
function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
</script>

<style scoped>
.wechat-account-page {
  padding-bottom: 20px;
}

.page-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.table-scroll {
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.cell-name {
  font-weight: 600;
  color: #303133;
}

.cell-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  color: #606266;
}

.cell-muted {
  color: #909399;
  font-size: 12px;
}

.row-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.form-hint {
  font-size: 11px;
  color: #c0c4cc;
  line-height: 1.5;
  margin-top: 4px;
}
</style>
