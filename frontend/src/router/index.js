// frontend/src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/register', component: () => import('../pages/Register.vue') },
  { path: '/login', component: () => import('../pages/Login.vue') },
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    children: [
      {
        path: '',
        component: () => import('../pages/Dashboard.vue'),
        meta: { requiresAuth: false }
      },
      {
        path: 'profile',
        component: () => import('../pages/profile/Profile.vue'),
        meta: { requiresAuth: true }
      },
      {
        path: 'files',
        component: () => import('../pages/files/FileList.vue'),
        meta: { requiresAuth: true }
      },
      {
        path: 'files/:id',
        component: () => import('../pages/files/FilePreview.vue'),
        props: true,
        meta: { requiresAuth: true }
      },
      {
        path: 'articles',
        component: () => import('../pages/articles/ArticleList.vue'),
        meta: { requiresAuth: false }
      },
      {
        path: 'articles/new',
        component: () => import('../pages/articles/ArticleEditor.vue'),
        meta: { requiresAuth: true }
      },
      {
        path: 'articles/:id',
        component: () => import('../pages/articles/ArticleDetail.vue'),
        props: true,
        meta: { requiresAuth: false }
      },
      {
        path: 'chat',
        component: () => import('../pages/chat/Chat.vue'),
        meta: { requiresAuth: true }
      },
      {
        path: 'admin',
        component: () => import('../layouts/AdminLayout.vue'),
        meta: { requiresAuth: true, requiresAdmin: true },
        children: [
          { path: '', redirect: '/admin/dashboard' },
          { path: 'dashboard', component: () => import('../pages/admin/Dashboard.vue') },
          { path: 'articles', component: () => import('../pages/admin/ArticlesManage.vue') },
          { path: 'users', component: () => import('../pages/admin/UsersManage.vue') },
          { path: 'files', component: () => import('../pages/admin/FilesManage.vue') },
          { path: 'chat', component: () => import('../pages/admin/ChatManage.vue') },
          { path: 'config', component: () => import('../pages/admin/SiteConfig.vue') }
        ]
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const auth = useAuthStore()

  // 公开页面直接放行（不需要认证的页面）
  if (to.meta.requiresAuth === false) {
    return next()
  }

  // 需要认证的页面：先尝试获取用户信息
  if (!auth.isAuthenticated) {
    try {
      await auth.fetchUser()
      // 获取成功，继续检查权限
    } catch (e) {
      // 获取失败，说明未登录或 token 失效，跳转登录页
      return next('/login')
    }
  }

  // 管理员权限检查
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return next('/')
  }

  next()
})

export default router