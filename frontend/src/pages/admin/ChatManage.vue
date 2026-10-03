<!-- ChatManage：聊天管理页，只负责取聊天记录（分页）、删除单条与清空全部，展示交给通用表格零件。 -->
<template>
  <div>
    <PageHeader title="聊天管理" />

    <Toolbar>
      <button type="button" @click="reload">刷新</button>
      <button type="button" class="danger" :disabled="messages.length === 0" @click="clearAll">
        清空所有记录
      </button>
    </Toolbar>

    <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
    <p v-if="notice" class="success-msg">{{ notice }}</p>

    <DataTable :columns="columns" :rows="messages" empty-text="暂无聊天记录" cell-padding="11px 12px">
      <template #cell-is_recalled="{ row }">{{ row.is_recalled ? '已撤回' : '正常' }}</template>
      <template #cell-created_at="{ row }">{{ formatDateTime(row.created_at) }}</template>
      <template #actions="{ row }">
        <button type="button" class="danger" @click="removeMessage(row)">删除</button>
      </template>
    </DataTable>

    <LoadMore :total="total" :loaded="messages.length" @load="loadMore" />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import DataTable from '@/components/common/DataTable.vue'
import LoadMore from '@/components/common/LoadMore.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import Toolbar from '@/components/common/Toolbar.vue'
import { formatDateTime } from '@/utils/format'
import request from '@/utils/request'

const PAGE_SIZE = 20

// 表格列定义：content 列要换行，class 交给下面的 :deep() 控制
const columns = [
  { key: 'id', label: 'ID' },
  { key: 'username', label: '用户' },
  { key: 'content', label: '内容', class: 'content' },
  { key: 'is_recalled', label: '状态' },
  { key: 'created_at', label: '时间' },
]

const messages = ref([])
const total = ref(0)
const page = ref(1)
const errorMsg = ref('')
const notice = ref('')

async function fetchMessages({ append = false } = {}) {
  errorMsg.value = ''
  try {
    const data = await request.get('/admin/chat/messages', {
      params: { page: page.value, size: PAGE_SIZE },
    })
    messages.value = append ? [...messages.value, ...data.items] : data.items
    total.value = data.total
  } catch (error) {
    errorMsg.value = error.message
  }
}

function reload() {
  page.value = 1
  fetchMessages()
}

function loadMore() {
  page.value += 1
  fetchMessages({ append: true })
}

async function removeMessage(message) {
  try {
    await request.delete(`/admin/chat/messages/${message.id}`)
    reload()
  } catch (error) {
    errorMsg.value = error.message
  }
}

async function clearAll() {
  if (!window.confirm('确定清空所有聊天记录？该操作不可恢复。')) return
  notice.value = ''
  try {
    // 后端提供 /admin/chat/clear
    const data = await request.delete('/admin/chat/clear')
    notice.value = data.message
    reload()
  } catch (error) {
    errorMsg.value = error.message
  }
}

onMounted(reload)
</script>

<style scoped>
/* 聊天内容列太长时换行 */
:deep(.content) { max-width: 340px; word-break: break-word; }
td button { padding: 5px 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-tertiary); color: var(--text); cursor: pointer; font-size: 13px; }
td button.danger { color: var(--danger); }
.error-msg { color: var(--danger); margin-bottom: 12px; }
.success-msg { color: var(--success); margin-bottom: 12px; }
</style>
