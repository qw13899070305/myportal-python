<!-- FilesManage：文件管理页，只负责取文件列表（分页/搜索）、删除与清理回收站，展示交给通用表格零件。 -->
<template>
  <div>
    <PageHeader title="文件管理" />

    <Toolbar wrap>
      <input v-model="search" placeholder="搜索文件..." @keyup.enter="reload" />
      <button type="button" @click="reload">搜索</button>
      <button type="button" class="danger" @click="cleanup">清理回收站</button>
    </Toolbar>

    <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
    <p v-if="notice" class="success-msg">{{ notice }}</p>

    <DataTable :columns="columns" :rows="files" empty-text="暂无文件" cell-padding="11px 12px">
      <template #cell-name="{ row }">{{ fileIcon(row.name) }} {{ row.name }}</template>
      <template #cell-category="{ row }">
        {{ categoryIcon(row.category) }} {{ categoryLabel(row.category) }}
      </template>
      <template #cell-uploader="{ row }">{{ row.uploader || '-' }}</template>
      <template #cell-size="{ row }">{{ formatSize(row.size) }}</template>
      <template #cell-upload_time="{ row }">{{ formatDateTime(row.upload_time) }}</template>
      <template #actions="{ row }">
        <button type="button" class="danger" @click="removeFile(row)">删除</button>
      </template>
    </DataTable>

    <LoadMore :total="total" :loaded="files.length" @load="loadMore" />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import DataTable from '@/components/common/DataTable.vue'
import LoadMore from '@/components/common/LoadMore.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import Toolbar from '@/components/common/Toolbar.vue'
import { categoryIcon, categoryLabel, fileIcon, formatDateTime, formatSize } from '@/utils/format'
import request from '@/utils/request'

const PAGE_SIZE = 20

// 表格列定义：name 列要换行，class 交给下面的 :deep() 控制
const columns = [
  { key: 'id', label: 'ID' },
  { key: 'name', label: '文件名', class: 'name' },
  { key: 'category', label: '分类' },
  { key: 'uploader', label: '上传者' },
  { key: 'size', label: '大小' },
  { key: 'upload_time', label: '上传时间' },
]

const files = ref([])
const total = ref(0)
const page = ref(1)
const search = ref('')
const errorMsg = ref('')
const notice = ref('')

async function fetchFiles({ append = false } = {}) {
  errorMsg.value = ''
  try {
    const data = await request.get('/files/', {
      params: { page: page.value, size: PAGE_SIZE, search: search.value },
    })
    files.value = append ? [...files.value, ...data.items] : data.items
    total.value = data.total
  } catch (error) {
    errorMsg.value = error.message
  }
}

function reload() {
  page.value = 1
  fetchFiles()
}

function loadMore() {
  page.value += 1
  fetchFiles({ append: true })
}

async function removeFile(file) {
  if (!window.confirm(`确定把「${file.name}」移入回收站？`)) return
  try {
    await request.delete(`/files/${file.id}`)
    reload()
  } catch (error) {
    errorMsg.value = error.message
  }
}

async function cleanup() {
  if (!window.confirm('确定彻底删除回收站中的所有文件？该操作不可恢复。')) return
  notice.value = ''
  try {
    const data = await request.post('/admin/files/cleanup')
    notice.value = data.message
    reload()
  } catch (error) {
    errorMsg.value = error.message
  }
}

onMounted(reload)
</script>

<style scoped>
/* 文件名列太长时换行，避免撑破表格 */
:deep(.name) { max-width: 280px; word-break: break-all; }
td button { padding: 5px 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-tertiary); color: var(--text); cursor: pointer; font-size: 13px; }
td button.danger { color: var(--danger); }
.error-msg { color: var(--danger); margin-bottom: 12px; }
.success-msg { color: var(--success); margin-bottom: 12px; }
</style>
