<!-- AuditLog：审计日志页，只负责按筛选条件取日志（分页），筛选条与表格都交给小零件。 -->
<template>
  <div>
    <PageHeader title="审计日志" />

    <AuditFilterBar @filter="applyFilter" @reset="resetFilter" />

    <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>

    <DataTable
      :columns="columns"
      :rows="logs"
      empty-text="暂无日志"
      cell-padding="10px 12px"
      cell-font-size="13px"
    >
      <template #cell-created_at="{ row }">{{ formatDateTime(row.created_at) }}</template>
      <template #cell-username="{ row }">{{ row.username || (row.user_id ? `#${row.user_id}` : '系统') }}</template>
      <template #cell-action="{ row }"><code>{{ row.action }}</code></template>
      <template #cell-detail="{ row }">{{ row.detail || '-' }}</template>
      <template #cell-ip_address="{ row }">{{ row.ip_address || '-' }}</template>
    </DataTable>

    <LoadMore :total="total" :loaded="logs.length" @load="loadMore" />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import AuditFilterBar from '@/components/admin/AuditFilterBar.vue'
import DataTable from '@/components/common/DataTable.vue'
import LoadMore from '@/components/common/LoadMore.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { formatDateTime } from '@/utils/format'
import request from '@/utils/request'

const PAGE_SIZE = 20

// 表格列定义：detail 列要换行，class 交给下面的 :deep() 控制
const columns = [
  { key: 'id', label: 'ID' },
  { key: 'created_at', label: '时间' },
  { key: 'username', label: '操作者' },
  { key: 'action', label: '动作' },
  { key: 'detail', label: '详情', class: 'detail' },
  { key: 'ip_address', label: 'IP' },
]

const logs = ref([])
const total = ref(0)
const page = ref(1)
const filterAction = ref('')
const filterUserId = ref('')
const errorMsg = ref('')

async function fetchLogs({ append = false } = {}) {
  errorMsg.value = ''
  try {
    const params = { page: page.value, limit: PAGE_SIZE }
    if (filterAction.value.trim()) params.action = filterAction.value.trim()
    if (filterUserId.value !== '') params.user_id = Number(filterUserId.value)
    const data = await request.get('/audit/', { params })
    logs.value = append ? [...logs.value, ...data.items] : data.items
    total.value = data.total
  } catch (error) {
    errorMsg.value = error.message
  }
}

function reload() {
  page.value = 1
  fetchLogs()
}

// 筛选条把输入值抛过来，存下来后从第一页重查
function applyFilter({ action, userId }) {
  filterAction.value = action
  filterUserId.value = userId
  reload()
}

function resetFilter() {
  filterAction.value = ''
  filterUserId.value = ''
  reload()
}

function loadMore() {
  page.value += 1
  fetchLogs({ append: true })
}

onMounted(reload)
</script>

<style scoped>
/* 详情列太长时换行 */
:deep(.detail) { max-width: 320px; word-break: break-word; color: var(--text-secondary); }
code { background: var(--bg-tertiary); padding: 1px 6px; border-radius: 4px; font-size: 12px; }
.error-msg { color: var(--danger); margin-bottom: 12px; }
</style>
