<template>
  <div class="chat-page">
    <div class="chat-header">
      <h1>聊天室</h1>
      <span class="online-count">🟢 {{ onlineCount }} 人在线</span>
    </div>
    <div class="messages" ref="msgList">
      <div v-for="msg in messages" :key="msg.id" class="msg" :class="{ recalled: msg.is_recalled }">
        <template v-if="msg.is_recalled">
          <em class="recalled-text">消息已撤回</em>
        </template>
        <template v-else>
          <strong>{{ msg.username }}</strong>
          <span class="msg-content" v-html="renderContent(msg.content)"></span>
          <span class="time">{{ formatTime(msg.time) }}</span>
          <button v-if="msg.user_id === auth.user?.id && canRecall(msg.time)" class="recall-btn" @click="recall(msg.id)">撤回</button>
        </template>
      </div>
      <div v-if="messages.length === 0" class="empty-chat">暂无消息，发送第一条吧</div>
    </div>
    <div class="input-area">
      <input v-model="text" @keyup.enter="send" placeholder="输入消息，@用户名 提及某人..." />
      <button @click="send" class="send-btn">
        <span class="btn-text">发送</span>
        <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { io } from 'socket.io-client'
import axios from 'axios'

const auth = useAuthStore()
const messages = ref([])
const text = ref('')
const msgList = ref(null)
const onlineCount = ref(1)

const backendUrl = window.location.protocol + '//' + window.location.hostname + ':8000'
const socket = io(backendUrl, {
  path: '/ws/socket.io',
  transports: ['websocket', 'polling']
})

socket.on('connect', () => {
  socket.emit('join', { user_id: auth.user?.id || 1 })
})

socket.on('chat_message', (msg) => {
  messages.value.push(msg)
  nextTick(() => {
    if (msgList.value) msgList.value.scrollTop = msgList.value.scrollHeight
  })
})

socket.on('message_revoked', ({ id }) => {
  const msg = messages.value.find(m => m.id === id)
  if (msg) msg.is_recalled = true
})

socket.on('user_joined', () => onlineCount.value++)
socket.on('user_left', () => onlineCount.value = Math.max(1, onlineCount.value - 1))

onMounted(async () => {
  try {
    const res = await axios.get('/api/v1/chat/history', {
      headers: { Authorization: `Bearer ${auth.token}` }
    })
    messages.value = res.data.items || []
  } catch (e) {}
})

function send() {
  if (!text.value.trim()) return
  socket.emit('send_message', { content: text.value })
  text.value = ''
}

function recall(id) {
  socket.emit('revoke_message', { id })
}

function canRecall(timeStr) {
  return Date.now() - new Date(timeStr).getTime() < 5 * 60 * 1000
}

function formatTime(t) { return new Date(t).toLocaleTimeString() }
function renderContent(content) { return content.replace(/@(\w+)/g, '<span class="mention">@$1</span>') }
</script>

<style scoped>
.chat-page { max-width: 700px; margin: 0 auto; display: flex; flex-direction: column; height: calc(100vh - var(--header-height) - 100px); }
.chat-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
h1 { font-size: 22px; }
.online-count { font-size: 14px; color: var(--success); }
.messages { flex: 1; overflow-y: auto; background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 12px; padding: 16px; }
.msg { margin-bottom: 12px; line-height: 1.5; position: relative; }
.msg strong { color: var(--primary); margin-right: 6px; }
.time { font-size: 11px; color: var(--text-tertiary); margin-left: 8px; }
.recalled-text { color: var(--text-secondary); font-style: italic; }
.recall-btn { font-size: 11px; background: transparent; color: var(--danger); border: none; cursor: pointer; margin-left: 8px; }
.mention { color: var(--primary); font-weight: 600; }
.empty-chat { text-align: center; color: var(--text-secondary); padding: 40px 0; }
.input-area { display: flex; gap: 10px; margin-top: 12px; }
input { flex: 1; padding: 12px 16px; border: 1px solid var(--border); border-radius: 12px; background: var(--bg-secondary); color: var(--text); }
.send-btn { background: #4f46e5; color: white; border: none; border-radius: 12px; padding: 0 20px; cursor: pointer; display: flex; align-items: center; gap: 6px; font-weight: 600; min-width: 60px; justify-content: center; }
.send-btn:hover { background: #4338ca; }
.btn-icon { display: none; }
@media (max-width: 600px) { .btn-text { display: none; } .btn-icon { display: block; } }
</style>
