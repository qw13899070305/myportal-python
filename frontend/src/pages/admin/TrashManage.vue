<!-- TrashManage：回收站页，只负责取回收站列表（分页）、恢复、彻底删除与清空，展示交给通用表格零件。 -->
<template>
  <div>
    <PageHeader title="回收站" />

    <Toolbar>
      <button type="button" @click="reload">刷新</button>
      <button type="button" class="danger" :disabled="items.length === 0" @click="empty">
        清空回收站
      </button>
    </Toolbar>

    <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
    <p v-if="notice" class="success-msg">{{ notice }}</p>

    <DataTable :columns="columns" :rows="items" empty-text="回收站是空的" cell-padding="11px 12px">
      <template #cell-name="{ row }">{{ fileIcon(row.name) }} {{ row.name }}</template>
      <template #cell-size="{ row }">{{ formatSize(row.size) }}</template>
      <template #cell-deleted_time="{ row }">{{ formatDateTime(row.deleted_time) }}</template>
      <template #actions="{ row }">
        <div class="actions">
          <button type="button" @click="restore(row)">恢复</button>
          <button type="button" class="danger" @click="purge(row)">彻底删除</button>
        </div>
      </template>
    </DataTable>

    <LoadMore :total="total" :loaded="items.length" @load="loadMore" />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import DataTable from '@/components/common/DataTable.vue'
import LoadMore from '@/components/common/LoadMore.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import Toolbar from '@/components/common/Toolbar.vue'
import { fileIcon, formatDateTime, formatSize } from '@/utils/format'
import request from '@/utils/request'

const PAGE_SIZE = 20

// 表格列定义：name 列要换行，class 交给下面的 :deep() 控制
const columns = [
  { key: 'id', label: 'ID' },
  { key: 'name', label: '文件名', class: 'name' },
  { key: 'size', label: '大小' },
  { key: 'deleted_time', label: '删除时间' },
]

const items = ref([])
const total = ref(0)
const page = ref(1)
const errorMsg = ref('')
const notice = ref('')

async function fetchTrash({ append = false } = {}) {
  errorMsg.value = ''
  try {
    const data = await request.get('/trash/', {
      params: { page: page.value, limit: PAGE_SIZE },
    })
    items.value = append ? [...items.value, ...data.items] : data.items
    total.value = data.total
  } catch (error) {
    errorMsg.value = error.message
  }
}

function reload() {
  page.value = 1
  fetchTrash()
}

function loadMore() {
  page.value += 1
  fetchTrash({ append: true })
}

async function restore(item) {
  notice.value = ''
  try {
    await request.post(`/trash/restore/${item.id}`)
    notice.value = `已恢复「${item.name}」`
    reload()
  } catch (error) {
    errorMsg.value = error.message
  }
}

async function purge(item) {
  if (!window.confirm(`确定彻底删除「${item.name}」？该操作不可恢复。`)) return
  notice.value = ''
  try {
    await request.delete(`/trash/permanent/${item.id}`)
    reload()
  } catch (error) {
    errorMsg.value = error.message
  }
}

async function empty() {
  if (!window.confirm('确定清空回收站？所有文件都会被彻底删除。')) return
  notice.value = ''
  try {
    const data = await request.delete('/trash/')
    notice.value = data.message
    reload()
  } catch (error) {
    errorMsg.value = error.message
  }
}

onMounted(reload)
</script>

<style scoped>
/* 文件名列太长时换行；两个操作按钮排成一行 */
:deep(.name) { max-width: 260px; word-break: break-all; }
.actions { display: flex; gap: 6px; }
td button { padding: 5px 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-tertiary); color: var(--text); cursor: pointer; font-size: 13px; }
td button.danger { color: var(--danger); }
.error-msg { color: var(--danger); margin-bottom: 12px; }
.success-msg { color: var(--success); margin-bottom: 12px; }
</style>
