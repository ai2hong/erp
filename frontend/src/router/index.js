import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '',          redirect: '/dashboard' },
      { path: 'dashboard', name: 'Dashboard',  component: () => import('@/views/DashboardView.vue') },
      { path: 'sale',      name: 'Sale',        component: () => import('@/views/SaleView.vue') },
      { path: 'customer',  name: 'Customer',    component: () => import('@/views/CustomerView.vue') },
      { path: 'unpaid',    name: 'Unpaid',      component: () => import('@/views/UnpaidView.vue') },
      { path: 'reserve',   name: 'Reserve',     component: () => import('@/views/ReservationView.vue') },
      { path: 'stock',     name: 'Stock',       component: () => import('@/views/StockView.vue') },
      { path: 'transfers', name: 'Transfers',   component: () => import('@/views/TransfersView.vue') },
      { path: 'dayclose',  name: 'DayClose',    component: () => import('@/views/DayCloseView.vue') },
      { path: 'approval',  name: 'Approval',    component: () => import('@/views/ApprovalView.vue') },
      { path: 'staff',     name: 'Staff',       component: () => import('@/views/StaffView.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 로그인 가드
router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isLoggedIn) {
    return '/login'
  }
})

export default router
