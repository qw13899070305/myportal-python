<!-- ShareDialog：分享结果弹窗零件，只展示下载链接并负责复制，关闭由父组件处理。 -->
<template>
  <div class="modal-mask" @click.self="emit('close')">
    <div class="modal">
      <h3>分享链接</h3>
      <p class="muted">
        把下面的链接发给别人即可下载（有效期至 {{ formatDateTime(share.expire_at) }}）。
      </p>
      <input :value="share.url" readonly @focus="$event.target.select()" />
      <div class="modal-actions">
        <button type="button" @click="emit('close')">关闭</button>
        <button type="button" class="primary" @click="copy">复制链接</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useToast } from 'vue-toastification'

import { formatDateTime } from '@/utils/format'

const props = defineProps({
  //: 分享接口返回结果，需要 url / expire_at
  share: { type: Object, required: true },
})
const emit = defineEmits(['close'])

const toast = useToast()

async function copy() {
  const url = props.share?.url
  if (!url) return
  try {
    await navigator.clipboard.writeText(url)
    toast.success('链接已复制')
  } catch {
    toast.info('复制失败，请手动选中链接复制')
  }
}
</script>

<style scoped>
.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 300; padding: 20px; }
.modal { background: var(--bg-secondary); border-radius: var(--radius); padding: 24px; width: 380px; max-width: 100%; border: 1px solid var(--border); }
.modal h3 { margin-bottom: 14px; }
.muted { color: var(--text-secondary); font-size: 13px; margin-bottom: 10px; }
.modal input { width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg); color: var(--text); }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 16px; }
.modal-actions button { padding: 8px 18px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-secondary); color: var(--text); cursor: pointer; }
.modal-actions button.primary { background: var(--primary); color: #fff; border-color: var(--primary); }
</style>
