<script setup>
import { ref } from 'vue'
import LoginView from './components/LoginView.vue'
import SuccessionView from './components/SuccessionView.vue'
import PromotionAgentView from './components/PromotionAgentView.vue'
import RiskView from './components/RiskView.vue'
import TrainingView from './components/TrainingView.vue'
import EmployeeView from './components/EmployeeView.vue'
import PotentialView from './components/PotentialView.vue'

const isLoggedIn = ref(localStorage.getItem('shixun_logged_in') === 'true')
const currentView = ref(localStorage.getItem('shixun_current_view') || 'potential')

const navItems = [
  { id: 'potential', icon: '▦', label: '人才潜力评估与岗位风险研判' },
  { id: 'succession', icon: '↗', label: '继任计划' },
  { id: 'promotionAgent', icon: '★', label: '晋升决策辅助' },
  { id: 'training', icon: '◆', label: '培训发展' },
  { id: 'risk', icon: '!', label: '风险预警' },
  { id: 'employee', icon: '⌕', label: '查询员工' },
]

const viewTitles = {
  potential: '人才潜力评估与岗位风险研判',
  succession: '继任计划',
  promotionAgent: '晋升决策辅助 Agent',
  training: '培训发展',
  risk: '风险预警',
  employee: '员工信息查询',
}

function onLoginSuccess() {
  isLoggedIn.value = true
  localStorage.setItem('shixun_logged_in', 'true')
}

function switchView(viewId) {
  currentView.value = viewId
  localStorage.setItem('shixun_current_view', viewId)
}

async function handleLogout() {
  try {
    await fetch('/api/auth/logout', { method: 'POST' })
  } catch {}
  isLoggedIn.value = false
  localStorage.removeItem('shixun_logged_in')
  localStorage.removeItem('shixun_current_view')
}
</script>

<template>
  <LoginView v-if="!isLoggedIn" @login-success="onLoginSuccess" />

  <div v-else class="app-layout">
    <aside class="sidebar">
      <div class="sidebar-brand">
        <span class="brand-icon">HR</span>
        <div>
          <p class="brand-title">人才梯队平台</p>
          <p class="brand-sub">HR 智能驱动</p>
        </div>
      </div>

      <nav class="sidebar-nav">
        <div
          v-for="item in navItems"
          :key="item.id"
          class="nav-item"
          :class="{ active: currentView === item.id }"
          @click="switchView(item.id)"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </div>
      </nav>

      <div class="sidebar-footer">
        <div class="user-info">
          <span class="user-avatar">HR</span>
          <div>
            <p class="user-name">管理员</p>
            <p class="user-role">HR 系统</p>
          </div>
        </div>
        <button class="logout-btn" @click="handleLogout">退出登录</button>
      </div>
    </aside>

    <main class="main-content">
      <header class="content-header">
        <h1>{{ viewTitles[currentView] }}</h1>
      </header>
      <KeepAlive>
        <PotentialView v-if="currentView === 'potential'" />
        <SuccessionView v-else-if="currentView === 'succession'" />
        <PromotionAgentView v-else-if="currentView === 'promotionAgent'" />
        <TrainingView v-else-if="currentView === 'training'" />
        <RiskView v-else-if="currentView === 'risk'" />
        <EmployeeView v-else-if="currentView === 'employee'" />
      </KeepAlive>
    </main>
  </div>
</template>
