<template>
  <div v-if="auth.isAuthenticated" class="bell">
    <button
      class="bell-button"
      type="button"
      :title="t('common.notifications')"
      :aria-label="t('common.notifications')"
      @click="toggle"
    >
      <span>🔔</span>
      <span v-if="unread > 0" class="badge">{{ unread > 99 ? '99+' : unread }}</span>
    </button>

    <div v-if="open" class="panel">
      <header class="panel-header">
        <strong>{{ t('common.notifications') }}</strong>
        <button type="button" class="link" :disabled="unread === 0" @click="markAllRead">
          {{ t('common.markAllRead') }}
        </button>
      </header>

      <p v-if="loading" class="hint">{{ t('common.loading') }}</p>
      <p v-else-if="items.length === 0" class="hint">{{ t('common.noNotifications') }}</p>
      <ul v-else class="list">
        <li
          v-for="item in items"
          :key="item.id"
          :class="{ unread: !item.is_read }"
          @click="markRead(item)"
        >
          <p class="content">{{ item.content }}</p>
          <small class="time">{{ formatDateTime(item.created_at) }}</small>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { useAuthStore } from '@/stores/auth'
import { formatDateTime } from '@/utils/format'
import request from '@/utils/request'

const auth = useAuthStore()
const { t } = useI18n()

const open = ref(false)
const loading = ref(false)
const unread = ref(0)
const items = ref([])
let timer = null

async function loadUnread() {
  if (!auth.isAuthenticated) {
    unread.value = 0
    return
  }
  try {
    const data = await request.get('/notifications/unread-count')
    unread.value = data.unread || 0
  } catch {
    // 静默失败：通知角标不应打断主流程
  }
}

async function loadList() {
  loading.value = true
  try {
    const data = await request.get('/notifications/', { params: { size: 10 } })
    items.value = data.items || []
    unread.value = data.unread || 0
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

function toggle() {
  open.value = !open.value
  if (open.value) {
    loadList()
  }
}

async function markRead(item) {
  if (item.is_read) return
  try {
    await request.post(`/notifications/${item.id}/read`)
    item.is_read = true
    unread.value = Math.max(0, unread.value - 1)
  } catch {
    // 忽略
  }
}

async function markAllRead() {
  try {
    await request.post('/notifications/read-all')
    items.value = items.value.map((item) => ({ ...item, is_read: true }))
    unread.value = 0
  } catch {
    // 忽略
  }
}

onMounted(() => {
  loadUnread()
  timer = window.setInterval(loadUnread, 60000)
})

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<style scoped>
.bell { position: relative; }
.bell-button { position: relative; width: 36px; height: 36px; border: none; background: transparent; border-radius: var(--radius-sm); cursor: pointer; font-size: 17px; color: var(--text-secondary); }
.bell-button:hover { background: var(--bg-tertiary); }
.badge { position: absolute; top: 2px; right: 0; min-width: 16px; height: 16px; padding: 0 4px; border-radius: 8px; background: var(--danger); color: #fff; font-size: 10px; line-height: 16px; text-align: center; }
.panel { position: absolute; right: 0; top: 44px; width: 320px; max-height: 420px; overflow-y: auto; background: var(--bg-secondary); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow-lg); z-index: 200; }
.panel-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 14px; border-bottom: 1px solid var(--border); }
.link { background: none; border: none; color: var(--primary); font-size: 13px; cursor: pointer; }
.link:disabled { color: var(--text-tertiary); cursor: not-allowed; }
.hint { padding: 20px; text-align: center; color: var(--text-secondary); font-size: 14px; }
.list { list-style: none; margin: 0; padding: 0; }
.list li { padding: 10px 14px; border-bottom: 1px solid var(--border); cursor: pointer; }
.list li:last-child { border-bottom: none; }
.list li:hover { background: var(--bg-tertiary); }
.list li.unread { background: var(--primary-light); }
.content { font-size: 14px; margin: 0 0 4px; }
.time { color: var(--text-tertiary); font-size: 12px; }
</style>
