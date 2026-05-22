<template>
  <div class="admin-layout">
    <aside class="admin-sidebar">
      <h3>管理后台</h3>
      <router-link to="/admin/dashboard">📊 仪表盘</router-link>
      <router-link to="/admin/articles">📝 文章管理</router-link>
      <router-link to="/admin/users">👥 用户管理</router-link>
      <router-link to="/admin/files">📁 文件管理</router-link>
      <router-link to="/admin/chat">💬 聊天管理</router-link>
      <router-link to="/admin/config">⚙️ 站点配置</router-link>
    </aside>
    <main class="admin-content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.admin-layout { display: flex; min-height: calc(100vh - var(--header-height) - 48px); }
.admin-sidebar { width: 200px; background: var(--bg-secondary); border-right: 1px solid var(--border); padding: 20px; display: flex; flex-direction: column; gap: 8px; }
.admin-sidebar a { padding: 8px 12px; border-radius: var(--radius-sm); color: var(--text); }
.admin-sidebar a.router-link-active { background: var(--primary); color: white; }
.admin-content { flex: 1; padding: 24px; }
</style>
