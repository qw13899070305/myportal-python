<!-- UsersManage：用户管理页，只负责取用户列表（分页/搜索）和启停用户，展示交给通用表格零件。 -->
<template>
  <div>
    <PageHeader title="用户管理" />

    <Toolbar>
      <input v-model="search" placeholder="搜索用户名..." @keyup.enter="reload" />
      <button type="button" @click="reload">搜索</button>
    </Toolbar>

    <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>

    <DataTable :columns="columns" :rows="users" empty-text="没有匹配的用户">
      <template #cell-email="{ row }">{{ row.email || '-' }}</template>
      <template #cell-roles="{ row }">{{ row.roles.join('、') || '-' }}</template>
      <template #cell-status="{ row }">
        <span :class="['status', row.is_active ? 'active' : 'inactive']">
          {{ row.is_active ? '正常' : '已禁用' }}
        </span>
      </template>
      <template #actions="{ row }">
        <button type="button" @click="toggleActive(row)">{{ row.is_active ? '禁用' : '启用' }}</button>
      </template>
    </DataTable>

    <LoadMore :total="total" :loaded="users.length" @load="loadMore" />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import DataTable from '@/components/common/DataTable.vue'
import LoadMore from '@/components/common/LoadMore.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import Toolbar from '@/components/common/Toolbar.vue'
import request from '@/utils/request'

const PAGE_SIZE = 20

// 表格列定义：#cell-<key> 插槽负责需要加工的单元格
const columns = [
  { key: 'id', label: 'ID' },
  { key: 'username', label: '用户名' },
  { key: 'email', label: '邮箱' },
  { key: 'roles', label: '角色' },
  { key: 'status', label: '状态' },
]

const users = ref([])
const total = ref(0)
const page = ref(1)
const search = ref('')
const errorMsg = ref('')

async function fetchUsers({ append = false } = {}) {
  errorMsg.value = ''
  try {
    const data = await request.get('/admin/users', {
      params: { page: page.value, size: PAGE_SIZE, search: search.value },
    })
    users.value = append ? [...users.value, ...data.items] : data.items
    total.value = data.total
  } catch (error) {
    errorMsg.value = error.message
  }
}

function reload() {
  page.value = 1
  fetchUsers()
}

function loadMore() {
  page.value += 1
  fetchUsers({ append: true })
}

async function toggleActive(user) {
  try {
    const updated = await request.post(`/admin/users/${user.id}/toggle-active`)
    Object.assign(user, updated)
  } catch (error) {
    errorMsg.value = error.message
  }
}

onMounted(reload)
</script>

<style scoped>
.status { font-size: 12px; padding: 2px 8px; border-radius: 10px; }
.status.active { background: var(--success-light); color: var(--success); }
.status.inactive { background: var(--danger-light); color: var(--danger); }
td button { padding: 6px 14px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-tertiary); color: var(--text); cursor: pointer; }
.error-msg { color: var(--danger); margin-bottom: 12px; }
</style>
