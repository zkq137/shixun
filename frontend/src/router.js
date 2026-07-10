import { createRouter, createWebHistory } from 'vue-router'
import DashboardPage from './pages/DashboardPage.vue'
import RiskOverviewPage from './pages/RiskOverviewPage.vue'
import RiskListPage from './pages/RiskListPage.vue'
import RiskEmployeeDetailPage from './pages/RiskEmployeeDetailPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: DashboardPage
    },
    {
      path: '/risk-overview',
      name: 'risk-overview',
      component: RiskOverviewPage
    },
    {
      path: '/risk-list',
      name: 'risk-list',
      component: RiskListPage
    },
    {
      path: '/risk-detail/:employee',
      name: 'risk-detail',
      component: RiskEmployeeDetailPage,
      props: true
    }
  ]
})

export default router
