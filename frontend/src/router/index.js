/**
 * 路由实例：创建 router、挂上守卫并导出（路由表见 ./routes，守卫见 ./guards）。
 */
import { createRouter, createWebHistory } from 'vue-router'

import { setupGuards } from './guards'
import { routes } from './routes'

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

setupGuards(router)

export default router
