<!-- FileUploader：上传按钮零件，负责选文件 + 逐个 POST /files/upload，把成功数量与失败明细交给父组件提示。 -->
<template>
  <label class="upload-btn">
    <input type="file" multiple @change="handleUpload" />
    <span>＋ 上传文件</span>
  </label>
</template>

<script setup>
import request from '@/utils/request'

//: upload-start 让父组件先清空旧提示；progress 报告进度；uploaded 携带 { count, failed }
const emit = defineEmits(['upload-start', 'progress', 'uploaded'])

async function handleUpload(event) {
  const selected = Array.from(event.target.files || [])
  if (selected.length === 0) return

  emit('upload-start')
  const failed = []

  for (const [index, file] of selected.entries()) {
    const form = new FormData()
    form.append('file', file)
    try {
      await request.post('/files/upload', form, {
        // 不要手写 Content-Type：浏览器必须自己带上 multipart 的 boundary。
        // 手机录像动辄几百 MB，默认 15 秒超时会直接把大文件掐断，这里不设超时。
        timeout: 0,
        onUploadProgress: (event) => {
          if (!event.total) return
          emit('progress', {
            name: file.name,
            index: index + 1,
            total: selected.length,
            percent: Math.round((event.loaded / event.total) * 100),
          })
        },
      })
    } catch (error) {
      failed.push(`${file.name}：${error.message}`)
    }
  }

  event.target.value = ''
  emit('uploaded', { count: selected.length, failed })
}
</script>

<style scoped>
.upload-btn { display: inline-flex; align-items: center; background: var(--primary); color: #fff; padding: 10px 18px; border-radius: var(--radius-sm); cursor: pointer; font-size: 14px; font-weight: 600; }
.upload-btn input { display: none; }
</style>
