<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { fetchUsers } from '@/api/auth'
import { fetchDocuments, uploadDocument, removeDocument } from '@/api/documents'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const activeTab = ref('docs')
const users = ref([])
const docs = ref([])
const loading = ref(false)
const uploading = ref(false)

const ACCEPT = '.txt,.md,.pdf,.docx'

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

async function loadDocs() {
  docs.value = await fetchDocuments()
}
async function loadUsers() {
  users.value = await fetchUsers()
}

onMounted(async () => {
  if (auth.role !== 'admin') {
    ElMessage.error('仅管理员可访问知识库管理')
    return router.push('/chat')
  }
  loading.value = true
  try {
    await Promise.all([loadDocs(), loadUsers()])
  } finally {
    loading.value = false
  }
})

async function handleUpload(options) {
  uploading.value = true
  try {
    const doc = await uploadDocument(options.file)
    if (doc.status === 'failed') {
      ElMessage.warning(`处理失败：${doc.error || '未知错误'}`)
    } else {
      ElMessage.success(`《${doc.filename}》入库完成，共 ${doc.chunk_count} 个分块`)
    }
    await loadDocs()
  } catch {
    // 错误提示由 axios 拦截器统一处理
  } finally {
    uploading.value = false
  }
}

function beforeUpload(file) {
  const ext = file.name.split('.').pop().toLowerCase()
  const allowed = ['txt', 'md', 'pdf', 'docx']
  if (!allowed.includes(ext)) {
    ElMessage.warning('仅支持 txt / md / pdf / docx 格式')
    return false
  }
  return true
}

async function handleDelete(row) {
  await ElMessageBox.confirm(
    `确认删除《${row.filename}》？其向量数据将一并清除。`,
    '删除文档',
    { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
  )
  await removeDocument(row.id)
  ElMessage.success('文档已删除')
  await loadDocs()
}
</script>

<template>
  <div class="admin-page">
    <header class="topbar">
      <div class="title">知识库管理</div>
      <div class="spacer" />
      <el-button text @click="router.push('/chat')">返回问答</el-button>
      <el-dropdown>
        <span class="user-chip">{{ auth.username }}</span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="auth.clearSession(); router.push('/login')">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </header>

    <main class="admin-main">
      <el-card class="main-card">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="知识库文档" name="docs">
            <div class="toolbar">
              <el-upload
                :show-file-list="false"
                :http-request="handleUpload"
                :before-upload="beforeUpload"
                :accept="ACCEPT"
              >
                <el-button type="primary" :icon="UploadFilled" :loading="uploading">
                  上传文档
                </el-button>
              </el-upload>
              <el-button @click="loadDocs">刷新</el-button>
              <span class="hint">支持 txt / md / pdf / docx，上传后自动解析、切分、向量化</span>
            </div>

            <el-table :data="docs" v-loading="loading" size="default">
              <el-table-column prop="id" label="ID" width="60" />
              <el-table-column prop="filename" label="文件名" min-width="200" show-overflow-tooltip />
              <el-table-column label="类型" width="80">
                <template #default="{ row }">
                  <el-tag size="small" type="info">{{ row.file_type }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="大小" width="100">
                <template #default="{ row }">{{ formatSize(row.size) }}</template>
              </el-table-column>
              <el-table-column prop="chunk_count" label="分块数" width="80" />
              <el-table-column label="状态" width="90">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'ready' ? 'success' : 'danger'" size="small">
                    {{ row.status === 'ready' ? '就绪' : '失败' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="上传时间" width="160" />
              <el-table-column label="操作" width="90" fixed="right">
                <template #default="{ row }">
                  <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane :label="`注册用户（${users.length}）`" name="users">
            <el-table :data="users" v-loading="loading" size="default">
              <el-table-column prop="id" label="ID" width="60" />
              <el-table-column prop="username" label="用户名" />
              <el-table-column label="角色" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.role === 'admin' ? 'warning' : 'info'" size="small">
                    {{ row.role }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="注册时间" width="180" />
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </main>
  </div>
</template>

<style scoped>
.admin-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
}
.topbar {
  height: 56px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px;
  border-bottom: 1px solid #e4e7ed;
  background: #fff;
}
.title {
  font-weight: 500;
  font-size: 15px;
}
.spacer {
  flex: 1;
}
.user-chip {
  cursor: pointer;
  font-size: 14px;
}
.admin-main {
  flex: 1;
  overflow: auto;
  padding: 20px;
  background: #f5f7fa;
}
.main-card {
  max-width: 1000px;
  margin: 0 auto;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.hint {
  font-size: 12px;
  color: #909399;
}
</style>