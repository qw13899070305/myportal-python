<template>
  <div class="chat-page">
    <h1>聊天室</h1>
    <div class="messages" ref="msgList">
      <div v-for="msg in messages" :key="msg.id" class="msg">
        <strong>{{ msg.username }}</strong>
        <span class="msg-content">{{ msg.content }}</span>
        <span class="time">{{ new Date(msg.time).toLocaleTimeString() }}</span>
      </div>
      <div v-if="messages.length === 0" class="empty-chat">暂无消息，发送第一条吧</div>
    </div>
    <div class="input-area">
      <input
        v-model="text"
        @keyup.enter="send"
        placeholder="输入消息..."
        class="chat-input"
      />
      <button @click="send" class="send-btn">
        <span class="btn-text">发送</span>
        <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
          <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { io } from 'socket.io-client'

const auth = useAuthStore()
const socket = io('/', { path: '/ws/socket.io' })
const messages = ref([])
const text = ref('')
const msgList = ref(null)

socket.on('chat_message', (msg) => {
  messages.value.push(msg)
  nextTick(() => {
    if (msgList.value) msgList.value.scrollTop = msgList.value.scrollHeight
  })
})

const send = () => {
  if (!text.value.trim()) return
  socket.emit('send_message', { content: text.value })
  text.value = ''
}
</script>

<style scoped>
.chat-page {
  max-width: 700px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--header-height) - 100px);
}
h1 { margin-bottom: 16px; flex-shrink: 0; }
.messages {
  flex: 1;
  overflow-y: auto;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
}
.msg {
  margin-bottom: 12px;
  line-height: 1.5;
}
.msg strong {
  color: var(--primary);
  margin-right: 6px;
}
.msg-content {
  color: var(--text);
}
.time {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-left: 8px;
}
.empty-chat {
  text-align: center;
  color: var(--text-secondary);
  padding: 40px 0;
}
.input-area {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}
.chat-input {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--bg-secondary);
  color: var(--text);
  font-size: 15px;
  outline: none;
}
.chat-input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-light);
}
.send-btn {
  background: var(--primary);
  color: white;
  border: none;
  border-radius: 12px;
  padding: 0 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  transition: 0.2s;
  min-width: 80px;
  justify-content: center;
}
.send-btn:hover {
  background: var(--primary-hover);
  transform: translateY(-1px);
}
.btn-text {
  font-size: 15px;
}
.btn-icon {
  display: none;
}

/* 移动端优化 */
@media (max-width: 600px) {
  .chat-page {
    height: calc(100vh - var(--header-height) - 160px);
    padding: 0 8px;
  }
  .send-btn {
    min-width: 50px;
    padding: 0 14px;
  }
  .btn-text {
    display: none;
  }
  .btn-icon {
    display: block;
  }
}
</style>
