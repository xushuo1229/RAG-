<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { checkUsername, login, register } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const mode = ref('login')
const form = ref({ username: '', password: '', confirm: '' })
const loading = ref(false)
const health = ref('检测中...')

onMounted(async () => {
  try {
    const res = await fetch('/api/health')
    const data = await res.json()
    health.value = `后端已连接 · ${data.app} v${data.version}`
  } catch {
    health.value = '后端未启动'
  }
})

const usernameStatus = ref('') // '' | 'checking' | 'ok' | 'taken'

function resetForm() {
  form.value = { username: '', password: '', confirm: '' }
  usernameStatus.value = ''
}

// 密码强度：按长度与字符类型组合分为 弱 / 中 / 强
const passwordStrength = computed(() => {
  const p = form.value.password
  if (!p) return { score: 0, label: '' }
  let types = 0
  if (/[a-z]/.test(p)) types += 1
  if (/[A-Z]/.test(p)) types += 1
  if (/[0-9]/.test(p)) types += 1
  if (/[^a-zA-Z0-9]/.test(p)) types += 1
  if (p.length >= 8 && types >= 3) return { score: 3, label: '强' }
  if (p.length >= 6 && types >= 2) return { score: 2, label: '中' }
  return { score: 1, label: '弱' }
})

// 用户名失焦时实时查重
async function checkName() {
  if (mode.value !== 'register') return
  const name = form.value.username.trim()
  if (name.length < 2) {
    usernameStatus.value = ''
    return
  }
  usernameStatus.value = 'checking'
  try {
    const { exists } = await checkUsername(name)
    usernameStatus.value = exists ? 'taken' : 'ok'
  } catch {
    usernameStatus.value = ''
  }
}

function goHome(data) {
  auth.setSession(data)
  router.push(data.role === 'admin' ? '/admin' : '/chat')
}

async function handleSubmit() {
  const { username, password, confirm } = form.value
  if (!username || !password) return ElMessage.warning('请输入用户名和密码')
  if (mode.value === 'register') {
    if (password.length < 6) return ElMessage.warning('密码至少 6 位')
    if (password !== confirm) return ElMessage.warning('两次输入的密码不一致')
    if (usernameStatus.value === 'taken') return ElMessage.warning('该用户名已被注册')
  }
  loading.value = true
  try {
    if (mode.value === 'login') {
      const data = await login({ username, password })
      ElMessage.success(`欢迎回来，${data.username}`)
      goHome(data)
    } else {
      await register({ username, password })
      // 注册成功后自动登录，免去新手重复输入用户名密码
      const data = await login({ username, password })
      ElMessage.success(`注册成功，欢迎你，${data.username}`)
      goHome(data)
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <el-card class="login-card">
      <h2>RAG 知识库问答系统</h2>
      <p class="sub">电商商品知识库 · LangChain + Milvus</p>

      <el-tabs v-model="mode" stretch @tab-change="resetForm">
        <el-tab-pane label="登录" name="login" />
        <el-tab-pane label="注册" name="register" />
      </el-tabs>

      <el-form label-position="top" @submit.prevent>
        <el-form-item label="用户名">
          <el-input
            v-model="form.username"
            placeholder="2-32 位中文、字母、数字、下划线"
            @blur="checkName"
          />
          <span v-if="usernameStatus === 'taken'" class="name-hint taken">该用户名已被注册</span>
          <span v-else-if="usernameStatus === 'ok'" class="name-hint ok">用户名可用</span>
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="至少 6 位"
            @keyup.enter="handleSubmit"
          />
          <div v-if="mode === 'register' && form.password" class="pwd-strength">
            <span class="bars">
              <i
                v-for="n in 3"
                :key="n"
                :class="['bar', n <= passwordStrength.score ? 'on' : '', 'lv' + passwordStrength.score]"
              />
            </span>
            <span class="pwd-label" :class="'lv' + passwordStrength.score">{{ passwordStrength.label }}</span>
          </div>
        </el-form-item>
        <el-form-item v-if="mode === 'register'" label="确认密码">
          <el-input
            v-model="form.confirm"
            type="password"
            show-password
            placeholder="再次输入密码"
            @keyup.enter="handleSubmit"
          />
        </el-form-item>
        <el-button type="primary" class="submit-btn" :loading="loading" @click="handleSubmit">
          {{ mode === 'login' ? '登 录' : '注 册' }}
        </el-button>
      </el-form>

      <p class="health">{{ health }}</p>
    </el-card>
  </div>
</template>

<style scoped>
.login-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1d2b64, #f8cdda);
}
.login-card {
  width: 380px;
}
h2 {
  text-align: center;
  margin: 4px 0;
}
.sub {
  text-align: center;
  color: #909399;
  font-size: 13px;
  margin-bottom: 12px;
}
.submit-btn {
  width: 100%;
  margin-top: 4px;
}
.name-hint {
  font-size: 12px;
}
.name-hint.taken {
  color: #f56c6c;
}
.name-hint.ok {
  color: #67c23a;
}
.pwd-strength {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}
.bars {
  display: flex;
  gap: 3px;
}
.bar {
  width: 42px;
  height: 4px;
  border-radius: 2px;
  background: #e4e7ed;
}
.bar.on.lv1 {
  background: #f56c6c;
}
.bar.on.lv2 {
  background: #e6a23c;
}
.bar.on.lv3 {
  background: #67c23a;
}
.pwd-label {
  font-size: 12px;
}
.pwd-label.lv1 {
  color: #f56c6c;
}
.pwd-label.lv2 {
  color: #e6a23c;
}
.pwd-label.lv3 {
  color: #67c23a;
}
.health {
  text-align: center;
  font-size: 12px;
  color: #c0c4cc;
  margin-top: 16px;
}
</style>
