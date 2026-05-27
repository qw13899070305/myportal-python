import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/login', component: () => import('../pages/Login.vue') },
  { path: '/register', component: () => import('../pages/Register.vue') },
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    children: [
      {
        path: '',
        component: () => import('../pages/Dashboard.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'chat',
        component: () => import('../pages/chat/Chat.vue'),
        meta: { requiresAuth: true },
      },
      // ... 其他路由
    ],
  },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to, from, next) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth !== false) {
    if (!auth.isAuthenticated) {
      try {
        await auth.fetchUser()
      } catch {
        return next('/login')
      }
    }
  }
  next()
})

export default router