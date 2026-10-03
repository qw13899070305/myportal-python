<template>
  <div class="chat-container">
    <div class="chat-header">
      <h1>聊天室</h1>
      <span class="status" :class="connected ? 'online' : 'offline'">
        {{ connected ? '已连接' : '连接中...' }}
      </span>
      <span class="online-count" v-if="onlineCount > 0">在线 {{ onlineCount }} 人</span>
    </div>

    <div ref="msgList" class="message-list" @scroll="handleScroll">
      <p v-if="loadingHistory" class="hint">加载历史...</p>
      <p v-else-if="!hasMore" class="hint">没有更多历史消息了</p>

      <div
        v-for="msg in messages"
        :key="msg.id"
        class="message"
        :class="{ mine: msg.user_id === auth.user?.id }"
      >
        <div class="bubble">
          <strong class="author">{{ msg.username }}</strong>
          <span class="content">{{ msg.content }}</span>
          <span class="time">{{ formatDateTime(msg.created_at || msg.time) }}</span>
        </div>
        <button
          v-if="msg.user_id === auth.user?.id"
          type="button"
          class="recall"
          title="撤回消息"
          @click="recall(msg)"
        >撤回</button>
      </div>
    </div>

    <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>

    <div class="input-area">
      <input
        v-model="draft"
        :maxlength="maxLength"
        placeholder="输入消息，@用户名 可以提醒对方..."
        @keyup.enter="send"
      />
      <button type="button" :disabled="!canSend" @click="send">发送</button>
    </div>
  </div>
</template>

<script setup>
/**
 * 实时聊天页面。
 *
 * 连接细节都在 ``@/utils/realtime`` 里，本组件只处理业务：
 * 历史记录分页、消息渲染、发送与撤回。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useToast } from 'vue-toastification'

import { useAuthStore } from '@/stores/auth'
import { formatDateTime } from '@/utils/format'
import { createChatSocket } from '@/utils/realtime'
import request from '@/utils/request'

const PAGE_SIZE = 30
const MAX_LENGTH = 500

const auth = useAuthStore()
const toast = useToast()

const messages = ref([])
const draft = ref('')
const page = ref(1)
const hasMore = ref(true)
const loadingHistory = ref(false)
const errorMsg = ref('')
const msgList = ref(null)
const connected = ref(false)
const onlineCount = ref(0)
const maxLength = MAX_LENGTH

let chat = null

const canSend = computed(() => draft.value.trim().length > 0)

function scrollToBottom() {
  nextTick(() => {
    const el = msgList.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function appendMessage(payload) {
  if (!payload || messages.value.some((item) => item.id === payload.id)) return
  messages.value.push(payload)
  onlineCount.value = Math.max(onlineCount.value, 1)
  scrollToBottom()
}

async function loadHistory({ prepend = false } = {}) {
  if (loadingHistory.value) return
  if (prepend && !hasMore.value) return

  loadingHistory.value = true
  try {
    const data = await request.get('/chat/messages', {
      params: { page: page.value, page_size: PAGE_SIZE },
    })
    const batch = data.items || []
    messages.value = prepend ? [...batch, ...messages.value] : batch
    if (batch.length < PAGE_SIZE) hasMore.value = false
    if (!prepend) scrollToBottom()
  } catch (error) {
    errorMsg.value = error.message
  } finally {
    loadingHistory.value = false
  }
}

function handleScroll() {
  const el = msgList.value
  if (el && el.scrollTop <= 0 && messages.value.length > 0) {
    // 向上翻页：记录当前高度，加载完成后保持视口位置
    const previousHeight = el.scrollHeight
    page.value += 1
    loadHistory({ prepend: true }).then(() => {
      nextTick(() => {
        if (el) el.scrollTop = el.scrollHeight - previousHeight
      })
    })
  }
}

function send() {
  if (!canSend.value) return
  if (!chat?.connected) {
    errorMsg.value = '连接尚未就绪，请稍后重试'
    return
  }
  chat.send(draft.value.trim())
  draft.value = ''
  errorMsg.value = ''
}

function recall(message) {
  if (!window.confirm('确定撤回这条消息？')) return
  chat?.recall(message.id)
}

onMounted(() => {
  loadHistory()

  chat = createChatSocket({
    token: auth.accessToken,
    handlers: {
      onMessage: appendMessage,
      onRevoked: (payload) => {
        messages.value = messages.value.filter((item) => item.id !== payload?.id)
      },
      onNotification: (payload) => {
        if (payload?.content) toast.info(payload.content)
      },
      onUserJoined: (payload) => {
        if (payload?.username) {
          onlineCount.value += 1
          toast.info(`${payload.username} 加入了聊天`)
        }
      },
      onStatusChange: (value) => {
        connected.value = value
      },
      onError: (message) => {
        errorMsg.value = message
      },
    },
  })
})

onBeforeUnmount(() => {
  chat?.close()
  chat = null
})
</script>

<style scoped>
.chat-container { display: flex; flex-direction: column; height: calc(100vh - var(--header-height) - 120px); min-height: 420px; }
.chat-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.chat-header h1 { font-size: 22px; }
.status { font-size: 12px; padding: 3px 10px; border-radius: 10px; }
.status.online { background: var(--success-light); color: var(--success); }
.status.offline { background: var(--warning-light); color: var(--warning); }
.online-count { font-size: 12px; color: var(--text-tertiary); }
.message-list { flex: 1; overflow-y: auto; padding: 12px; background: var(--bg-secondary); border: 1px solid var(--border); border-radius: var(--radius); display: flex; flex-direction: column; gap: 10px; }
.message { display: flex; align-items: flex-end; gap: 8px; }
.message.mine { flex-direction: row-reverse; }
.bubble { background: var(--bg-tertiary); border-radius: 10px; padding: 8px 12px; max-width: 70%; display: flex; flex-direction: column; gap: 2px; }
.message.mine .bubble { background: var(--primary-light); }
.author { font-size: 12px; color: var(--text-secondary); }
.content { font-size: 14px; word-break: break-word; white-space: pre-wrap; }
.time { font-size: 11px; color: var(--text-tertiary); }
.recall { background: none; border: none; color: var(--text-tertiary); font-size: 12px; cursor: pointer; }
.recall:hover { color: var(--danger); }
.input-area { display: flex; gap: 10px; margin-top: 12px; }
.input-area input { flex: 1; padding: 12px 14px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-secondary); color: var(--text); }
.input-area button { padding: 12px 26px; border: none; border-radius: var(--radius-sm); background: var(--primary); color: #fff; cursor: pointer; font-weight: 600; }
.input-area button:disabled { opacity: 0.5; cursor: not-allowed; }
.hint { text-align: center; color: var(--text-tertiary); font-size: 13px; padding: 8px 0; }
.error-msg { color: var(--danger); font-size: 13px; margin-top: 8px; }
</style>
