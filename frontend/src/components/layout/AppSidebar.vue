<!-- AppSidebar：左侧导航栏零件，只负责「品牌区 + 导航链接 + 底部用户信息」的展示，点击任何链接都通知父组件收起抽屉。 -->
<template>
  <aside class="sidebar" :class="{ open }">
    <div class="sidebar-brand">
      <span class="brand-icon">◈</span>
      <span class="brand-text">MyPortal</span>
    </div>

    <nav class="sidebar-nav">
      <router-link to="/" class="nav-link" @click="emit('close')">
        <svg class="nav-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
        <span>{{ t('nav.dashboard') }}</span>
      </router-link>

      <router-link to="/files" class="nav-link" @click="emit('close')">
        <svg class="nav-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>
        <span>{{ t('nav.files') }}</span>
      </router-link>

      <router-link to="/articles" class="nav-link" @click="emit('close')">
        <svg class="nav-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        <span>{{ t('nav.articles') }}</span>
      </router-link>

      <router-link to="/chat" class="nav-link" @click="emit('close')">
        <svg class="nav-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
        <span>{{ t('nav.chat') }}</span>
      </router-link>

      <router-link v-if="auth.isAdmin()" to="/admin" class="nav-link" @click="emit('close')">
        <svg class="nav-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
        <span>{{ t('nav.admin') }}</span>
      </router-link>
    </nav>

    <div class="sidebar-footer">
      <router-link v-if="auth.isAuthenticated" to="/profile" class="nav-link" @click="emit('close')">
        <img v-if="auth.user?.avatar_url" class="avatar-mini" :src="auth.user.avatar_url" alt="头像" />
        <div v-else class="avatar-mini">{{ initial }}</div>
        <span>{{ auth.user?.username }}</span>
      </router-link>
      <router-link v-else to="/login" class="nav-link" @click="emit('close')">
        <div class="avatar-mini">?</div>
        <span>{{ t('common.login') }}</span>
      </router-link>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { useAuthStore } from '@/stores/auth'

defineProps({
  //: 移动端抽屉是否展开（桌面端恒定可见）
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

const auth = useAuthStore()
const { t } = useI18n()

const initial = computed(() => auth.user?.username?.charAt(0)?.toUpperCase() || '?')
</script>

<style scoped>
.sidebar { width: var(--sidebar-width); min-width: var(--sidebar-width); background: var(--bg-secondary); border-right: 1px solid var(--border); display: flex; flex-direction: column; position: fixed; top: 0; left: 0; bottom: 0; z-index: 100; transition: transform var(--transition); }
.sidebar-brand { display: flex; align-items: center; gap: 10px; padding: 20px; border-bottom: 1px solid var(--border); }
.brand-icon { font-size: 22px; color: var(--primary); }
.brand-text { font-size: 18px; font-weight: 700; }
.sidebar-nav { flex: 1; padding: 12px; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; }
.nav-link { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: var(--radius-sm); color: var(--text-secondary); font-size: 14px; font-weight: 500; transition: all var(--transition); }
.nav-link:hover { background: var(--bg-tertiary); color: var(--text); }
.nav-link.router-link-active { background: var(--primary-light); color: var(--primary); }
.nav-svg { width: 18px; height: 18px; flex-shrink: 0; }
.sidebar-footer { padding: 12px; border-top: 1px solid var(--border); }
.avatar-mini { width: 28px; height: 28px; border-radius: 50%; background: var(--primary); color: white; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; flex-shrink: 0; object-fit: cover; }

@media (max-width: 768px) {
  .sidebar { transform: translateX(-100%); }
  .sidebar.open { transform: translateX(0); }
}
</style>
