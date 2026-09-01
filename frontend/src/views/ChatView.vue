<script setup>
import { nextTick, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ChatDotRound, Delete, Plus, Promotion, User } from '@element-plus/icons-vue'
import { changePassword } from '@/api/auth'
import { askStream, fetchConversations, fetchMessages, removeConversation } from '@/api/chat'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const conversations = ref([])
const currentConvId = ref(null)
const messages = ref([])
const input = ref('')
const sending = ref(false)
const msgBoxRef = ref(null)
const activeRef = ref(null)

const pwdDialog = ref(false)
const pwdForm = reactive({ old_password: '', new_password: '', confirm: '' })

onMounted(loadConversations)

function scrollToBottom() {
  nextTick(() => {
    if (msgBoxRef.value) msgBoxRef.value.scrollTop = msgBoxRef.value.scrollHeight
  })
}

async function loadConversations() {
  conversations.value = await fetchConversations()
}

async function selectConversation(id) {
  currentConvId.value = id
  const list = await fetchMessages(id)
  messages.value = list.map((m) => ({
    role: m.role,
    content: m.content,
    sources: m.sources || [],
    cached: m.cached,
  }))
  scrollToBottom()
}

function newChat() {
  currentConvId.value = null
  messages.value = []
}

async function handleDeleteConversation(id) {
  await ElMessageBox.confirm('确认删除该会话？', '删除会话', { type: 'warning' })
  await removeConversation(id)
  ElMessage.success('会话已删除')
  if (currentConvId.value === id) newChat()
  await loadConversations()
}

async function send() {
  const question = input.value.trim()
  if (!question || sending.value) return
  input.value = ''
  messages.value.push({ role: 'user', content: question, sources: [] })

  const assistantMsg = reactive({ role: 'assistant', content: '', sources: [], cached: false, related: [] })
  messages.value.push(assistantMsg)
  sending.value = true
  scrollToBottom()

  try {
    await askStream(
      { question, conversation_id: currentConvId.value },
      {
        onSources: (sources) => {
          assistantMsg.sources = sources
          scrollToBottom()
        },
        onDelta: (delta) => {
          assistantMsg.content += delta
          scrollToBottom()
        },
        onRelated: (list) => {
          assistantMsg.related = list
        },
        onDone: (data) => {
          if (!currentConvId.value) currentConvId.value = data.conversation_id
          assistantMsg.cached = data.cached
        },
        onError: (msg) => {
          assistantMsg.content = assistantMsg.content || `出错了：${msg}`
          ElMessage.error(msg)
        },
      },
    )
    await loadConversations()
  } catch (e) {
    assistantMsg.content = assistantMsg.content || '发送失败，请重试'
    ElMessage.error(e.message || '发送失败')
  } finally {
    sending.value = false
  }
}

async function handleChangePassword() {
  const { old_password, new_password, confirm } = pwdForm
  if (new_password.length < 6) return ElMessage.warning('新密码至少 6 位')
  if (new_password !== confirm) return ElMessage.warning('两次输入的新密码不一致')
  await changePassword({ old_password, new_password })
  ElMessage.success('密码修改成功，请重新登录')
  pwdDialog.value = false
  auth.clearSession()
  router.push('/login')
}

function handleLogout() {
  auth.clearSession()
  ElMessage.success('已退出登录')
  router.push('/login')
}

// 把回答中的引用标记 [n] 拆成文本/引用片段，用于高亮渲染
function parseCitations(text) {
  const parts = []
  const re = /\[(\d+)\]/g
  let last = 0
  let m
  while ((m = re.exec(text))) {
    if (m.index > last) parts.push({ type: 'text', text: text.slice(last, m.index) })
    parts.push({ type: 'cite', n: Number(m[1]) })
    last = m.index + m[0].length
  }
  if (last < text.length) parts.push({ type: 'text', text: text.slice(last) })
  return parts
}

// 点击引用标记：高亮对应来源并滚动到可见位置
function highlightSource(i, n) {
  activeRef.value = { i, n }
  nextTick(() => {
    document.getElementById(`src-${i}-${n - 1}`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  })
}

// 点击相似问题，填入输入框并重新提问
function askRelated(q) {
  input.value = q
  send()
}
</script>

<template>
  <div class="chat-page">
    <!-- 顶部栏 -->
    <header class="topbar">
      <div class="title">RAG 知识库问答</div>
      <div class="spacer" />
      <el-button v-if="auth.role === 'admin'" text @click="router.push('/admin')">知识库管理</el-button>
      <el-dropdown>
        <span class="user-chip">
          <el-icon><User /></el-icon>
          {{ auth.username }}
          <el-tag v-if="auth.role === 'admin'" size="small" type="warning">admin</el-tag>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="pwdDialog = true">修改密码</el-dropdown-item>
            <el-dropdown-item divided @click="handleLogout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </header>

    <div class="chat-body">
      <!-- 会话侧边栏 -->
      <aside class="sidebar">
        <el-button type="primary" class="new-btn" :icon="Plus" @click="newChat">新建对话</el-button>
        <div class="conv-list">
          <div
            v-for="c in conversations"
            :key="c.id"
            class="conv-item"
            :class="{ active: c.id === currentConvId }"
            @click="selectConversation(c.id)"
          >
            <el-icon><ChatDotRound /></el-icon>
            <span class="conv-title">{{ c.title }}</span>
            <el-icon class="del" @click.stop="handleDeleteConversation(c.id)"><Delete /></el-icon>
          </div>
          <el-empty v-if="!conversations.length" description="暂无会话" :image-size="60" />
        </div>
      </aside>

      <!-- 聊天区 -->
      <main class="chat-main">
        <div ref="msgBoxRef" class="msg-box">
          <div v-if="!messages.length" class="welcome">
            <h3>电商商品知识库问答</h3>
            <p>上传商品文档到知识库后，即可向它提问商品参数、价格、售后等问题</p>
          </div>

          <div v-for="(m, i) in messages" :key="i" class="msg-row" :class="m.role">
            <div class="bubble">
              <div class="content">
                <template v-for="(seg, si) in parseCitations(m.content)" :key="si">
                  <span v-if="seg.type === 'cite'" class="cite" @click="highlightSource(i, seg.n)">[{{ seg.n }}]</span>
                  <template v-else>{{ seg.text }}</template>
                </template>
              </div>

              <div v-if="m.role === 'assistant' && m.sources.length" class="sources">
                <span class="src-label">引用来源：</span>
                <el-popover
                  v-for="(s, si) in m.sources"
                  :key="si"
                  placement="top"
                  :width="320"
                  trigger="hover"
                >
                  <template #reference>
                    <el-tag
                      size="small"
                      type="info"
                      class="src-tag"
                      :class="{ 'src-active': activeRef && activeRef.i === i && activeRef.n === si + 1 }"
                    >
                      <span :id="`src-${i}-${si}`" class="src-num">[{{ si + 1 }}]</span>
                      {{ s.filename }}<span class="score">({{ s.score }})</span>
                    </el-tag>
                  </template>
                  <div class="src-text">{{ s.text }}</div>
                </el-popover>
              </div>

              <div v-if="m.role === 'assistant' && m.related && m.related.length" class="related">
                <span class="rel-label">相似问题：</span>
                <el-tag
                  v-for="(q, qi) in m.related"
                  :key="qi"
                  size="small"
                  class="rel-tag"
                  @click="askRelated(q)"
                >
                  {{ q }}
                </el-tag>
              </div>

              <div v-if="m.role === 'assistant' && m.cached" class="cached-tag">
                <el-tag size="small" type="success" effect="plain">命中语义缓存</el-tag>
              </div>
            </div>
          </div>
        </div>

        <footer class="input-bar">
          <el-input
            v-model="input"
            type="textarea"
            :rows="2"
            resize="none"
            placeholder="输入你的问题，Enter 发送，Shift+Enter 换行"
            @keydown.enter.exact.prevent="send"
          />
          <el-button
            type="primary"
            :icon="Promotion"
            :loading="sending"
            :disabled="!input.trim()"
            @click="send"
          >
            发送
          </el-button>
        </footer>
      </main>
    </div>

    <!-- 修改密码弹窗 -->
    <el-dialog v-model="pwdDialog" title="修改密码" width="360px">
      <el-form label-position="top">
        <el-form-item label="原密码">
          <el-input v-model="pwdForm.old_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="pwdForm.new_password" type="password" show-password placeholder="至少 6 位" />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="pwdForm.confirm" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdDialog = false">取消</el-button>
        <el-button type="primary" @click="handleChangePassword">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.chat-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
}
.topbar {
  height: 56px;
  display: flex;
  align-items: center;
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
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 14px;
  outline: none;
}
.chat-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}
.sidebar {
  width: 260px;
  border-right: 1px solid #e4e7ed;
  background: #fff;
  display: flex;
  flex-direction: column;
  padding: 12px;
}
.new-btn {
  width: 100%;
}
.conv-list {
  flex: 1;
  overflow: auto;
  margin-top: 12px;
}
.conv-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  color: #303133;
}
.conv-item:hover {
  background: #f5f7fa;
}
.conv-item.active {
  background: #ecf5ff;
  color: #409eff;
}
.conv-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.conv-item .del {
  visibility: hidden;
  color: #c0c4cc;
}
.conv-item:hover .del {
  visibility: visible;
}
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}
.msg-box {
  flex: 1;
  overflow: auto;
  padding: 20px;
}
.welcome {
  text-align: center;
  color: #909399;
  margin-top: 120px;
}
.welcome h3 {
  margin-bottom: 8px;
  color: #606266;
}
.msg-row {
  display: flex;
  margin-bottom: 16px;
}
.msg-row.user {
  justify-content: flex-end;
}
.msg-row.assistant {
  justify-content: flex-start;
}
.bubble {
  max-width: 72%;
  padding: 12px 14px;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}
.msg-row.user .bubble {
  background: #409eff;
  color: #fff;
}
.msg-row.assistant .bubble {
  background: #fff;
}
.content {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
  font-size: 14px;
}
.cite {
  color: #409eff;
  font-weight: 600;
  cursor: pointer;
  padding: 0 2px;
}
.cite:hover {
  text-decoration: underline;
}
.sources {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.src-label {
  font-size: 12px;
  color: #909399;
}
.src-tag {
  cursor: pointer;
}
.src-num {
  color: #409eff;
  font-weight: 600;
  margin-right: 2px;
}
.src-tag.src-active {
  border-color: #409eff;
  background: #ecf5ff;
  color: #409eff;
}
.score {
  color: #999;
  margin-left: 2px;
}
.src-text {
  font-size: 13px;
  line-height: 1.5;
  color: #606266;
}
.related {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.rel-label {
  font-size: 12px;
  color: #909399;
}
.rel-tag {
  cursor: pointer;
}
.cached-tag {
  margin-top: 8px;
}
.input-bar {
  display: flex;
  gap: 12px;
  padding: 14px 20px;
  border-top: 1px solid #e4e7ed;
  background: #fff;
  align-items: flex-end;
}
.input-bar .el-button {
  height: 54px;
  width: 88px;
}
</style>