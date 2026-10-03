<!-- FileList：文件管理页，只负责取列表数据（分页）、组合各个小零件、调用接口、维护弹窗开关状态。 -->
<template>
  <div class="page">
    <h1 class="page-title">文件管理</h1>

    <div class="toolbar">
      <FileUploader
        @upload-start="handleUploadStart"
        @progress="handleProgress"
        @uploaded="handleUploaded"
      />
      <FileSearchBar v-model="search" @search="reload" />
    </div>

    <!-- 分类标签：数字来自后端 /files/categories，与列表同一个统计口径 -->
    <div class="cat-tabs">
      <button
        type="button"
        class="cat-tab"
        :class="{ active: category === '' }"
        @click="switchCategory('')"
      >
        全部<span class="cat-count">{{ counts.total }}</span>
      </button>
      <button
        v-for="item in FILE_CATEGORIES"
        :key="item.key"
        type="button"
        class="cat-tab"
        :class="{ active: category === item.key }"
        @click="switchCategory(item.key)"
      >
        {{ item.icon }} {{ item.label }}<span class="cat-count">{{ counts[item.key] }}</span>
      </button>
    </div>

    <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
    <!-- 上传失败必须留在页面上：列表刷新会把 errorMsg 清掉，所以单独存一份 -->
    <p v-if="uploadError" class="error-msg">上传失败：{{ uploadError }}</p>
    <p v-if="uploadProgress" class="hint">{{ uploadProgress }}</p>
    <p v-if="uploadMsg" class="success-msg">{{ uploadMsg }}</p>
    <p v-if="loading" class="hint">加载中...</p>
    <p v-else-if="files.length === 0" class="hint">
      {{ category ? `「${categoryLabel(category)}」分类下暂无文件。` : '暂无文件，先上传一个吧。' }}
    </p>

    <div v-else class="file-grid">
      <FileCard
        v-for="item in files"
        :key="item.id"
        :file="item"
        @preview="openPreview"
        @share="share"
        @rename="openRename"
        @remove="removeFile"
        @contextmenu="openContextMenu"
      />
    </div>

    <div class="pager" v-if="total > files.length">
      <button type="button" :disabled="loading" @click="loadMore">加载更多</button>
    </div>

    <!-- 右键菜单：动作与卡片上的按钮完全一致 -->
    <FileContextMenu
      :visible="menu.visible"
      :x="menu.x"
      :y="menu.y"
      :items="menuItems"
      @select="runMenuAction"
      @close="menu.visible = false"
    />

    <RenameDialog
      v-if="renameTarget"
      :file="renameTarget"
      @close="renameTarget = null"
      @renamed="confirmRename"
    />

    <ShareDialog v-if="shareResult" :share="shareResult" @close="shareResult = null" />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'vue-toastification'

import FileCard from '@/components/files/FileCard.vue'
import FileContextMenu from '@/components/files/FileContextMenu.vue'
import FileSearchBar from '@/components/files/FileSearchBar.vue'
import FileUploader from '@/components/files/FileUploader.vue'
import RenameDialog from '@/components/files/RenameDialog.vue'
import ShareDialog from '@/components/files/ShareDialog.vue'
import { FILE_CATEGORIES, categoryLabel } from '@/utils/format'
import request from '@/utils/request'

const PAGE_SIZE = 24

const router = useRouter()
const toast = useToast()

const files = ref([])
const total = ref(0)
const page = ref(1)
const search = ref('')
//: 当前分类（空字符串 = 全部），值就是后端给的机器键
const category = ref('')
//: 各分类的计数（{ total, image, document, ... }），后端统计，前端只显示
const counts = ref({ total: 0 })
const loading = ref(false)
const errorMsg = ref('')
const uploadMsg = ref('')
const uploadError = ref('')
const uploadProgress = ref('')
const renameTarget = ref(null)
const shareResult = ref(null)

//: 右键菜单状态：位置 + 当前作用的文件
const menu = ref({ visible: false, x: 0, y: 0, file: null })

//: 菜单项与卡片按钮保持同一套动作
const menuItems = [
  { action: 'preview', label: '打开预览' },
  { action: 'share', label: '分享' },
  { action: 'rename', label: '重命名' },
  { action: 'remove', label: '删除', danger: true },
]

/** 在鼠标位置弹出右键菜单。 */
function openContextMenu(event, item) {
  menu.value = { visible: true, x: event.clientX, y: event.clientY, file: item }
}

/** 执行右键菜单选中的动作。 */
function runMenuAction(action) {
  const item = menu.value.file
  if (!item) return
  if (action === 'preview') openPreview(item)
  else if (action === 'share') share(item)
  else if (action === 'rename') openRename(item)
  else if (action === 'remove') removeFile(item)
}

async function fetchFiles({ append = false } = {}) {
  loading.value = true
  errorMsg.value = ''
  try {
    const data = await request.get('/files/', {
      params: {
        page: page.value,
        size: PAGE_SIZE,
        search: search.value,
        category: category.value,
      },
    })
    files.value = append ? [...files.value, ...data.items] : data.items
    total.value = data.total
  } catch (error) {
    errorMsg.value = error.message
  } finally {
    loading.value = false
  }
}

/** 拉分类计数（与列表同一个搜索条件，保证"标签上的数字"跟点进去看到的一致）。 */
async function fetchCounts() {
  try {
    const data = await request.get('/files/categories', { params: { search: search.value } })
    counts.value = Object.fromEntries([
      ['total', data.total],
      ...data.items.map((item) => [item.key, item.count]),
    ])
  } catch {
    // 计数失败不影响列表，静默即可
    counts.value = { total: total.value }
  }
}

/** 列表 + 计数一起刷新。 */
function refresh() {
  fetchFiles()
  fetchCounts()
}

function reload() {
  page.value = 1
  refresh()
}

/** 切换分类：回到第一页重新取，计数不用重取（口径没变）。 */
function switchCategory(key) {
  if (category.value === key) return
  category.value = key
  page.value = 1
  fetchFiles()
}

function loadMore() {
  page.value += 1
  fetchFiles({ append: true })
}

function openPreview(item) {
  router.push({ name: 'file-preview', params: { id: item.id } })
}

function openRename(item) {
  renameTarget.value = item
}

async function confirmRename(name) {
  try {
    await request.patch(`/files/${renameTarget.value.id}`, { name })
    renameTarget.value = null
    reload()
  } catch (error) {
    errorMsg.value = error.message
  }
}

async function removeFile(item) {
  if (!window.confirm(`确定把「${item.name}」移入回收站？`)) return
  try {
    await request.delete(`/files/${item.id}`)
    toast.success('已移入回收站')
    reload()
  } catch (error) {
    errorMsg.value = error.message
  }
}

async function share(item) {
  errorMsg.value = ''
  try {
    const data = await request.post('/share/create', { file_id: item.id })
    shareResult.value = {
      ...data,
      url: `${window.location.origin}/api/v1/share/download/${data.code}`,
    }
  } catch (error) {
    errorMsg.value = error.message
  }
}

/** 开始上传前清空旧提示（上传零件只发信号，文案仍归页面管）。 */
function handleUploadStart() {
  errorMsg.value = ''
  uploadMsg.value = ''
  uploadError.value = ''
  uploadProgress.value = '正在准备上传…'
}

/** 大文件上传中：把「第几个 / 进度」显示出来，否则手机用户以为卡死了。 */
function handleProgress({ name, index, total, percent }) {
  uploadProgress.value = `正在上传（${index}/${total}）${name} ${percent}%`
}

/** 上传结束：失败列错误，成功弹提示，最后统一刷新列表。 */
function handleUploaded({ count, failed }) {
  uploadProgress.value = ''
  if (failed.length > 0) {
    // 单独存一份：reload() 会把 errorMsg 清空，写在 errorMsg 里等于没提示
    uploadError.value = failed.join('；')
    toast.error(`${failed.length} 个文件上传失败：${failed[0]}`)
  } else {
    uploadMsg.value = `已上传 ${count} 个文件`
    toast.success(uploadMsg.value)
  }
  reload()
}

onMounted(reload)
</script>

<style scoped>
.page-title { font-size: 26px; font-weight: 700; margin-bottom: 24px; }
.toolbar { display: flex; gap: 14px; flex-wrap: wrap; align-items: center; margin-bottom: 14px; }
.cat-tabs { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 18px; }
.cat-tab { display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border: 1px solid var(--border); border-radius: 999px; background: var(--bg-secondary); color: var(--text-secondary); font-size: 13px; cursor: pointer; }
.cat-tab:hover { color: var(--text); }
.cat-tab.active { background: var(--primary); border-color: var(--primary); color: #fff; font-weight: 600; }
.cat-count { font-size: 12px; opacity: 0.75; }
.error-msg { color: var(--danger); margin-bottom: 12px; }
.success-msg { color: var(--success); margin-bottom: 12px; }
.hint { text-align: center; color: var(--text-secondary); padding: 40px 0; }
.file-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 14px; }
.pager { text-align: center; margin-top: 24px; }
.pager button { padding: 10px 28px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-secondary); color: var(--text); cursor: pointer; }
</style>
