<script setup>
import { ref } from 'vue'
import LoginView from './components/LoginView.vue'
import OverviewView from './components/OverviewView.vue'
import NineBoxView from './components/NineBoxView.vue'
import SuccessionView from './components/SuccessionView.vue'
import RiskView from './components/RiskView.vue'
import TrainingView from './components/TrainingView.vue'
import EmployeeView from './components/EmployeeView.vue'
import PotentialView from './components/PotentialView.vue'

// 从 localStorage 恢复登录状态
const isLoggedIn = ref(localStorage.getItem('shixun_logged_in') === 'true')
const currentView = ref(localStorage.getItem('shixun_current_view') || 'overview')

const navItems = [
  { id: 'overview', icon: '📊', label: '概览驾驶舱' },
  { id: 'ninebox', icon: '🎯', label: '人才九宫格' },
  { id: 'potential', icon: '🧠', label: '人才潜力' },
  { id: 'succession', icon: '👥', label: '继任计划' },
  { id: 'training', icon: '📚', label: '培训发展' },
  { id: 'risk', icon: '⚠️', label: '风险预警' },
  { id: 'employee', icon: '🔍', label: '查询员工' },
]

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
  <!-- 未登录 → 显示登录页 -->
  <LoginView v-if="!isLoggedIn" @login-success="onLoginSuccess" />

  <!-- 已登录 → 显示主界面 -->
  <div v-else class="app-layout">
    <aside class="sidebar">
      <div class="sidebar-brand">
        <span class="brand-icon">🏢</span>
        <div>
          <p class="brand-title">人才梯队平台</p>
          <p class="brand-sub">HR 智能驾驶舱</p>
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
          <span class="user-avatar">👤</span>
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
        <h1>
          <span v-if="currentView === 'overview'">📊 概览驾驶舱</span>
          <span v-else-if="currentView === 'ninebox'">🎯 人才九宫格</span>
          <span v-else-if="currentView === 'potential'">🧠 人才潜力</span>
          <span v-else-if="currentView === 'succession'">👥 继任计划</span>
          <span v-else-if="currentView === 'training'">📚 培训发展</span>
          <span v-else-if="currentView === 'risk'">⚠️ 风险预警</span>
          <span v-else-if="currentView === 'employee'">🔍 员工信息查询</span>
        </h1>
      </header>
      <OverviewView v-if="currentView === 'overview'" />
      <NineBoxView v-else-if="currentView === 'ninebox'" />
      <PotentialView v-else-if="currentView === 'potential'" />
      <SuccessionView v-else-if="currentView === 'succession'" />
      <TrainingView v-else-if="currentView === 'training'" />
      <RiskView v-else-if="currentView === 'risk'" />
      <EmployeeView v-else-if="currentView === 'employee'" />
    </main>
  </div>
</template>
