<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login, register } from '@/api/auth'
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

async function handleSubmit() {
  const { username, password, confirm } = form.value
  if (!username || !password) return ElMessage.warning('请输入用户名和密码')
  if (mode.value === 'register') {
    if (password.length < 6) return ElMessage.warning('密码至少 6 位')
    if (password !== confirm) return ElMessage.warning('两次输入的密码不一致')
  }
  loading.value = true
  try {
    if (mode.value === 'login') {
      const data = await login({ username, password })
      auth.setSession(data)
      ElMessage.success(`欢迎回来，${data.username}`)
      router.push(data.role === 'admin' ? '/admin' : '/chat')
    } else {
      await register({ username, password })
      ElMessage.success('注册成功，请登录')
      mode.value = 'login'
      form.value.confirm = ''
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

      <el-tabs v-model="mode" stretch>
        <el-tab-pane label="登录" name="login" />
        <el-tab-pane label="注册" name="register" />
      </el-tabs>

      <el-form label-position="top" @submit.prevent>
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="2-32 位中文、字母、数字、下划线" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="至少 6 位"
            @keyup.enter="handleSubmit"
          />
        </el-form-item>
        <el-form-item v-if="mode === 'register'" label="确认密码">
          <el-input v-model="form.confirm" type="password" show-password placeholder="再次输入密码" />
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
.health {
  text-align: center;
  font-size: 12px;
  color: #c0c4cc;
  margin-top: 16px;
}
</style>
