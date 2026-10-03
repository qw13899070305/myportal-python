<!--
  FilePreview：文件在线预览页。

  展示方式由**前端**决定（后端只给数据 / 字节流）：
  - 视频 / 音频 / 图片 → 浏览器原生控件，数据源是 /files/{id}/raw
  - 其余格式（PDF、Office、电子书…）→ iframe 加载后端渲染的 HTML 预览
-->
<template>
  <div class="preview-page">
    <div class="toolbar">
      <button type="button" class="back-btn" @click="$router.back()">← 返回</button>
      <span class="file-title" v-if="meta">{{ meta.name }}</span>
      <a class="download-btn" :href="downloadUrl">下载文件</a>
    </div>

    <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>

    <!--
      iframe / 播放器 / 图片都无法携带 Authorization 请求头，
      因此字节流与预览地址通过 ?token= 传递访问令牌
      （后端对应接口使用 get_current_user_flexible 依赖）。
    -->
    <video
      v-if="kind === 'video'"
      class="preview-media"
      :src="rawUrl"
      controls
      playsinline
      preload="metadata"
    >
      你的浏览器不支持播放这个视频，请下载后观看。
    </video>

    <audio
      v-else-if="kind === 'audio'"
      class="preview-audio"
      :src="rawUrl"
      controls
      preload="metadata"
    >
      你的浏览器不支持播放这个音频，请下载后收听。
    </audio>

    <img
      v-else-if="kind === 'image'"
      class="preview-image"
      :src="rawUrl"
      :alt="meta?.name || '图片预览'"
    />

    <iframe v-else-if="previewUrl" :src="previewUrl" class="preview-frame" title="文件预览"></iframe>
    <p v-else class="hint">正在准备预览…</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import { previewKind } from '@/utils/format'
import request from '@/utils/request'

const route = useRoute()
const auth = useAuthStore()

const meta = ref(null)
const errorMsg = ref('')

const fileId = computed(() => route.params.id)
const tokenQuery = computed(() =>
  auth.accessToken ? `?token=${encodeURIComponent(auth.accessToken)}` : '',
)
//: 后端渲染好的 HTML 预览（PDF / Office / 电子书 / 文本…）
const previewUrl = computed(() =>
  fileId.value ? `/api/v1/files/${fileId.value}/preview${tokenQuery.value}` : '',
)
//: 原始字节流（视频 / 音频 / 图片交给浏览器自己解码）
const rawUrl = computed(() =>
  fileId.value ? `/api/v1/files/${fileId.value}/raw${tokenQuery.value}` : '',
)
const downloadUrl = computed(() =>
  fileId.value ? `/api/v1/files/${fileId.value}/download${tokenQuery.value}` : '#',
)
const kind = computed(() => previewKind(meta.value?.name || ''))

onMounted(async () => {
  try {
    meta.value = await request.get(`/files/${fileId.value}`)
  } catch (error) {
    errorMsg.value = error.message
  }
})
</script>

<style scoped>
.preview-page { display: flex; flex-direction: column; gap: 12px; }
.toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.file-title { font-weight: 600; color: var(--text-secondary); font-size: 14px; word-break: break-all; }
.back-btn, .download-btn { padding: 8px 16px; border-radius: var(--radius-sm); font-size: 14px; cursor: pointer; text-decoration: none; }
.back-btn { background: var(--bg-secondary); border: 1px solid var(--border); color: var(--text); }
.download-btn { background: var(--primary); color: #fff; margin-left: auto; }
.error-msg { color: var(--danger); }
.hint { color: var(--text-secondary); padding: 40px 0; text-align: center; }
.preview-frame { width: 100%; height: calc(100vh - var(--header-height) - 140px); border: 1px solid var(--border); border-radius: var(--radius); background: #fff; }
.preview-media { width: 100%; max-height: calc(100vh - var(--header-height) - 160px); background: #000; border-radius: var(--radius); }
.preview-audio { width: 100%; margin-top: 24px; }
.preview-image { max-width: 100%; max-height: calc(100vh - var(--header-height) - 160px); object-fit: contain; background: var(--bg-secondary); border-radius: var(--radius); }
</style>
