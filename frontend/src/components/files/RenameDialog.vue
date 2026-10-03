<!-- RenameDialog：重命名弹窗零件，只收集新文件名并把结果抛给父组件，接口调用由父组件负责。 -->
<template>
  <div class="modal-mask" @click.self="emit('close')">
    <div class="modal">
      <h3>重命名</h3>
      <input v-model.trim="value" placeholder="新文件名" @keyup.enter="submit" />
      <div class="modal-actions">
        <button type="button" @click="emit('close')">取消</button>
        <button type="button" class="primary" @click="submit">确定</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  //: 待重命名的文件对象（用 name 作为输入框初值）
  file: { type: Object, required: true },
})
const emit = defineEmits(['close', 'renamed'])

const value = ref(props.file?.name || '')

function submit() {
  if (!value.value) return
  emit('renamed', value.value)
}
</script>

<style scoped>
.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 300; padding: 20px; }
.modal { background: var(--bg-secondary); border-radius: var(--radius); padding: 24px; width: 380px; max-width: 100%; border: 1px solid var(--border); }
.modal h3 { margin-bottom: 14px; }
.modal input { width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg); color: var(--text); }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 16px; }
.modal-actions button { padding: 8px 18px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-secondary); color: var(--text); cursor: pointer; }
.modal-actions button.primary { background: var(--primary); color: #fff; border-color: var(--primary); }
</style>
