<template>
  <div class="app-shell" :class="{ dark: appStore.isDark }">
    <div class="overlay" :class="{ visible: sidebarOpen }" @click="sidebarOpen = false"></div>
    <aside class="sidebar" :class="{ open: sidebarOpen }">
      <div class="sidebar-brand">
        <span class="brand-icon">◈</span>
        <span class="brand-text">MyPortal</span>
      </div>
      <nav class="sidebar-nav">
        <router-link to="/" class="nav-link" @click="sidebarOpen = false">
          <svg class="nav-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
          <span>仪表盘</span>
        </router-link>
        <router-link to="/files" class="nav-link" @click="sidebarOpen = false">
          <svg class="nav-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>
          <span>文件</span>
        </router-link>
        <router-link to="/articles" class="nav-link" @click="sidebarOpen = false">
          <svg class="nav-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          <span>文章</span>
        </router-link>
        <router-link to="/chat" class="nav-link" @click="sidebarOpen = false">
          <svg class="nav-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
          <span>聊天</span>
        </router-link>
        <router-link v-if="auth.isAdmin()" to="/admin" class="nav-link" @click="sidebarOpen = false">
          <svg class="nav-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
          <span>管理</span>
        </router-link>
      </nav>
      <div class="sidebar-footer">
        <router-link to="/profile" class="nav-link" @click="sidebarOpen = false">
          <div class="avatar-mini">{{ auth.user?.username?.charAt(0) }}</div>
          <span>{{ auth.user?.username }}</span>
        </router-link>
      </div>
    </aside>

    <div class="main-panel">
      <header class="topbar">
        <button class="menu-toggle" @click="sidebarOpen = !sidebarOpen">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="22" height="22"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        </button>
        <div class="topbar-actions">
          <button class="icon-btn" @click="appStore.toggleDark()" :title="appStore.isDark ? '亮色模式' : '暗色模式'">
            <svg v-if="!appStore.isDark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
          </button>
          <button class="icon-btn logout-btn" @click="handleLogout" title="退出登录">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
          </button>
        </div>
      </header>
      <main class="page-content">
        <router-view />
      </main>
    </div>

    <nav class="mobile-nav">
      <router-link to="/" class="mob-link">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="22" height="22"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
      </router-link>
      <router-link to="/files" class="mob-link">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="22" height="22"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>
      </router-link>
      <router-link to="/articles" class="mob-link">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="22" height="22"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
      </router-link>
      <router-link to="/chat" class="mob-link">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="22" height="22"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
      </router-link>
    </nav>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useAppStore } from '../stores/app'

const router = useRouter()
const auth = useAuthStore()
const appStore = useAppStore()
const sidebarOpen = ref(false)

function handleLogout() { auth.logout(); router.push('/login') }
</script>

<style scoped>
.app-shell { display: flex; min-height: 100vh; }
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 90; opacity: 0; pointer-events: none; transition: opacity var(--transition); }
.overlay.visible { opacity: 1; pointer-events: auto; }
.sidebar { width: var(--sidebar-width); min-width: var(--sidebar-width); background: var(--bg-secondary); border-right: 1px solid var(--border); display: flex; flex-direction: column; position: fixed; top: 0; left: 0; bottom: 0; z-index: 100; transition: transform var(--transition); backdrop-filter: blur(20px); background: var(--bg-secondary); }
.sidebar-brand { display: flex; align-items: center; gap: 10px; padding: 20px; border-bottom: 1px solid var(--border); }
.brand-icon { font-size: 22px; color: var(--primary); }
.brand-text { font-size: 18px; font-weight: 700; }
.sidebar-nav { flex: 1; padding: 12px; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; }
.nav-link { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: var(--radius-sm); color: var(--text-secondary); font-size: 14px; font-weight: 500; transition: all var(--transition); }
.nav-link:hover { background: var(--bg-tertiary); color: var(--text); }
.nav-link.router-link-active { background: var(--primary-light); color: var(--primary); }
.nav-svg { width: 18px; height: 18px; flex-shrink: 0; }
.sidebar-footer { padding: 12px; border-top: 1px solid var(--border); }
.avatar-mini { width: 28px; height: 28px; border-radius: 50%; background: var(--primary); color: white; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; flex-shrink: 0; }
.main-panel { flex: 1; margin-left: var(--sidebar-width); display: flex; flex-direction: column; min-height: 100vh; }
.topbar { height: var(--header-height); background: var(--bg-secondary); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 20px; position: sticky; top: 0; z-index: 50; backdrop-filter: blur(20px); }
.menu-toggle { display: none; background: none; color: var(--text); }
.topbar-actions { display: flex; align-items: center; gap: 8px; margin-left: auto; }
.icon-btn { width: 36px; height: 36px; border-radius: var(--radius-sm); background: transparent; color: var(--text-secondary); display: flex; align-items: center; justify-content: center; transition: all var(--transition); }
.icon-btn:hover { background: var(--bg-tertiary); color: var(--text); }
.logout-btn:hover { background: var(--danger-light); color: var(--danger); }
.page-content { flex: 1; padding: 28px; max-width: 1280px; width: 100%; margin: 0 auto; }
.mobile-nav { display: none; position: fixed; bottom: 0; left: 0; right: 0; background: var(--bg-secondary); border-top: 1px solid var(--border); z-index: 100; justify-content: space-around; padding: 8px 0; backdrop-filter: blur(20px); background: var(--bg-secondary); }
.mob-link { padding: 8px 16px; border-radius: var(--radius-sm); color: var(--text-tertiary); transition: all var(--transition); }
.mob-link.router-link-active { color: var(--primary); }

@media (max-width: 768px) {
  .sidebar { transform: translateX(-100%); }
  .sidebar.open { transform: translateX(0); }
  .menu-toggle { display: block; }
  .main-panel { margin-left: 0; }
  .mobile-nav { display: flex; }
  .page-content { padding: 16px; padding-bottom: 80px; }
}
</style>
