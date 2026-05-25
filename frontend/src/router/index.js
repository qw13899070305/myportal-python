import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/register', component: () => import('../pages/Register.vue') },
  { path: '/login', component: () => import('../pages/Login.vue') },
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    children: [
      { path: '', component: () => import('../pages/Dashboard.vue') },
      { path: 'profile', component: () => import('../pages/profile/Profile.vue') },
      { path: 'files', component: () => import('../pages/files/FileList.vue') },
      { path: 'files/:id', component: () => import('../pages/files/FilePreview.vue'), props: true },
      { path: 'articles', component: () => import('../pages/articles/ArticleList.vue') },
      { path: 'articles/new', component: () => import('../pages/articles/ArticleEditor.vue') },
      { path: 'articles/:id', component: () => import('../pages/articles/ArticleDetail.vue'), props: true },
      { path: 'chat', component: () => import('../pages/chat/Chat.vue') },
      {
        path: 'admin',
        component: () => import('../layouts/AdminLayout.vue'),
        meta: { requiresAdmin: true },
        children: [
          { path: '', redirect: '/admin/dashboard' },
          { path: 'dashboard', component: () => import('../pages/admin/Dashboard.vue') },
          { path: 'articles', component: () => import('../pages/admin/ArticlesManage.vue') },
          { path: 'users', component: () => import('../pages/admin/UsersManage.vue') },
      }
    ]
  }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to, from, next) => {
  const auth = useAuthStore()
  if (to.path === "/register" || to.path === "/login") { next(); return; }
  if (auth.token && (!auth.user || !auth.user.roles)) {
    try {
      await auth.fetchUser();
      next();
      return;
    } catch {
      auth.logout();
    }
  }
  if (!auth.token) { next("/login"); }
  else if (to.meta.requiresAdmin && !auth.isAdmin()) { next("/"); }
  else { next(); }
  const auth = useAuthStore()
  if (to.path === '/register' || to.path === '/login') {
    // 注册和登录页无需权限
    next()
    return
  }
  if (auth.token && (!auth.user || !auth.user.roles)) {
    try { await auth.fetchUser(); next(); return; } catch { try { await auth.fetchUser(); next(); return; } catch { auth.logout() } }
  }
  if (to.path !== '/login' && !auth.token) {
    next('/login')
  } else if (to.meta.requiresAdmin && !auth.isAdmin()) {
    next('/')
  } else {
    next()
  }
})

export default router
