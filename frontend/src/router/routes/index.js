/**
 * 路由表汇总：把 auth / main / admin 三块路由拼成一棵完整的路由树。
 */
import adminRoutes from './admin'
import authRoutes from './auth'
import mainRoutes from './main'

/**
 * 把后台路由并回主布局（'/'）的 children。
 *
 * 拆分前后台就是主布局的子路由，AdminLayout 因此渲染在 MainLayout 的页面区域内
 * （AdminLayout 的样式也是按“上方有顶栏”算高度的）。这里保持这一层级不变，
 * 只是把它挪到了独立文件里。
 */
function withAdminRoutes(routes) {
  return routes.map((route) => (
    route.path === '/'
      ? { ...route, children: [...route.children, ...adminRoutes] }
      : route
  ))
}

// 404 是 authRoutes 里的一员，但声明顺序上必须排在最后（与拆分前一致）
const notFoundRoutes = authRoutes.filter((route) => route.name === 'not-found')

/** 完整路由表：登录/注册 -> 主布局（含后台）-> 404 兜底。 */
export const routes = [
  ...authRoutes.filter((route) => route.name !== 'not-found'),
  ...withAdminRoutes(mainRoutes),
  ...notFoundRoutes,
]

export default routes
