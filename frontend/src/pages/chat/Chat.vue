<template>
  <div class="chat-container">
    <div class="message-list" ref="msgList" @scroll="handleScroll">
      <div v-if="loadingHistory" class="loading">加载历史...</div>
      <div v-for="msg in messages" :key="msg.id" class="message">
        <strong>{{ msg.username }}:</strong> {{ msg.content }}
        <span class="time">{{ msg.time }}</span>
      </div>
    </div>
    <div class="input-area">
      <input v-model="newMsg" @keyup.enter="send" placeholder="输入消息..." />
      <button @click="send">发送</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import request from '@/utils/request'
import io from 'socket.io-client'

const socket = io('/', { path: '/ws/socket.io', transports: ['websocket'] })
const messages = ref([])
const newMsg = ref('')
const page = ref(1)
const hasMore = ref(true)
const loadingHistory = ref(false)
const msgList = ref(null)

async function loadHistory() {
  if (!hasMore.value || loadingHistory.value) return
  loadingHistory.value = true
  try {
    const data = await request.get('/chat/messages', { params: { page: page.value, page_size: 30 } })
    if (data.length < 30) hasMore.value = false
    messages.value = [...data, ...messages.value]
    page.value++
  } finally {
    loadingHistory.value = false
  }
}

function handleScroll() {
  const el = msgList.value
  if (el && el.scrollTop === 0) {
    loadHistory()
  }
}

function send() {
  if (!newMsg.value.trim()) return
  socket.emit('send_message', { content: newMsg.value })
  newMsg.value = ''
}

onMounted(() => {
  loadHistory()
  socket.on('chat_message', (msg) => {
    messages.value.push(msg)
    nextTick(() => {
      msgList.value?.scrollTo({ top: msgList.value.scrollHeight, behavior: 'smooth' })
    })
  })
})
</script>

<style scoped>
.chat-container { display: flex; flex-direction: column; height: 100vh; }
.message-list { flex: 1; overflow-y: auto; padding: 10px; }
.message { margin-bottom: 8px; }
.time { color: #999; font-size: 12px; margin-left: 10px; }
.input-area { display: flex; padding: 10px; border-top: 1px solid #ccc; }
.input-area input { flex: 1; padding: 8px; }
</style>
