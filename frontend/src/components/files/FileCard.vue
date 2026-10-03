<!-- FileCard：单个文件卡片零件（图标 + 名称 + 分类/大小 + 分享/重命名/删除按钮），只负责展示与发出意图，不发请求。 -->
<template>
  <div
    class="file-card"
    @click="emit('preview', file)"
    @contextmenu.prevent="emit('contextmenu', $event, file)"
  >
    <span class="file-type">{{ fileIcon(file.name) }}</span>
    <span class="file-name" :title="file.name">{{ file.name }}</span>
    <span class="file-meta">
      <span class="file-cat" :title="`分类：${categoryLabel(file.category)}`">
        {{ categoryIcon(file.category) }} {{ categoryLabel(file.category) }}
      </span>
      · {{ formatSize(file.size) }}
    </span>
    <div class="file-actions" @click.stop>
      <button type="button" @click="emit('share', file)">分享</button>
      <button type="button" @click="emit('rename', file)">重命名</button>
      <button type="button" class="danger" @click="emit('remove', file)">删除</button>
    </div>
  </div>
</template>

<script setup>
import { categoryIcon, categoryLabel, fileIcon, formatSize } from '@/utils/format'

defineProps({
  //: 文件对象，需要 id / name / size / category
  file: { type: Object, required: true },
})
//: contextmenu 额外带上鼠标事件，供页面定位右键菜单
const emit = defineEmits(['preview', 'share', 'rename', 'remove', 'contextmenu'])
</script>

<style scoped>
.file-card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; text-align: center; cursor: pointer; transition: all var(--transition); display: flex; flex-direction: column; gap: 6px; align-items: center; }
.file-card:hover { border-color: var(--primary); box-shadow: var(--shadow); transform: translateY(-2px); }
.file-type { font-size: 34px; }
.file-name { font-size: 14px; font-weight: 500; word-break: break-all; }
.file-meta { font-size: 12px; color: var(--text-tertiary); }
.file-cat { color: var(--text-secondary); }
.file-actions { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; justify-content: center; }
.file-actions button { font-size: 12px; padding: 4px 10px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-tertiary); color: var(--text); cursor: pointer; }
.file-actions button.danger { color: var(--danger); border-color: var(--danger-light); }
</style>
