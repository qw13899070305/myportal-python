<!-- SiteBasicForm：站点基础信息表单零件，自己保存 /admin/config，只把保存结果通过 saved 事件抛出去。 -->
<template>
  <form class="card" @submit.prevent="save">
    <h3>基础信息</h3>
    <div class="form-group">
      <label>站点名称</label>
      <input v-model.trim="siteName" maxlength="100" />
    </div>

    <div class="form-group">
      <label>公告</label>
      <textarea v-model="announcement" rows="4" maxlength="2000"></textarea>
    </div>

    <div class="form-group">
      <label class="checkbox-label">
        <input type="checkbox" v-model="allowRegister" />
        允许新用户注册
      </label>
      <label class="checkbox-label">
        <input type="checkbox" v-model="allowUpload" />
        允许上传文件
      </label>
    </div>

    <p v-if="error || errorMsg" class="error-msg">{{ error || errorMsg }}</p>
    <p v-if="message" class="success-msg">{{ message }}</p>

    <button type="submit" :disabled="saving">{{ saving ? '保存中...' : '保存配置' }}</button>
  </form>
</template>

<script setup>
import { ref, watch } from 'vue'

import request from '@/utils/request'

const props = defineProps({
  // 父组件读到的站点配置
  config: { type: Object, default: () => ({}) },
  // 父组件读取配置失败时的提示，展示位置和原来一致
  error: { type: String, default: '' },
})

const emit = defineEmits(['saved'])

const siteName = ref('')
const announcement = ref('')
const allowRegister = ref(true)
const allowUpload = ref(true)
const saving = ref(false)
const message = ref('')
const errorMsg = ref('')

// 每次父组件换成新配置（首次加载、保存后刷新）都同步到表单
watch(() => props.config, (cfg) => {
  siteName.value = cfg.site_name || ''
  announcement.value = cfg.announcement || ''
  allowRegister.value = cfg.allow_register !== 'false'
  allowUpload.value = cfg.allow_upload !== 'false'
}, { immediate: true, deep: true })

async function save() {
  message.value = ''
  errorMsg.value = ''
  saving.value = true
  try {
    // 后端 GET/PUT/POST 都支持
    const data = await request.put('/admin/config', {
      site_name: siteName.value,
      announcement: announcement.value,
      allow_register: allowRegister.value,
      allow_upload: allowUpload.value,
    })
    siteName.value = data.site_name || ''
    announcement.value = data.announcement || ''
    message.value = '配置已保存'
    emit('saved', data)
  } catch (error) {
    errorMsg.value = error.message
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
h3 { margin-bottom: 14px; font-size: 16px; }
.card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 12px; padding: 24px; margin-bottom: 16px; }
.form-group { margin-bottom: 20px; }
label { display: block; font-weight: 600; margin-bottom: 8px; color: var(--text-secondary); }
input, textarea { width: 100%; padding: 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg); color: var(--text); font-size: 15px; }
textarea { resize: vertical; }
.checkbox-label { display: flex; align-items: center; gap: 8px; font-weight: 500; color: var(--text); margin-bottom: 10px; }
.checkbox-label input { width: auto; }
button { background: var(--primary); color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-weight: 600; }
button:disabled { opacity: 0.6; cursor: not-allowed; }
.success-msg { margin-top: 12px; color: var(--success); font-size: 14px; }
.error-msg { margin-bottom: 12px; color: var(--danger); font-size: 14px; }
</style>
