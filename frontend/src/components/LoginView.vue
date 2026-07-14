<script setup>
import { ref } from 'vue'
import FaceCamera from './FaceCamera.vue'

const emit = defineEmits(['login-success'])

// ── 登录方式切换 ──
const loginMode = ref('face') // 'simple' | 'face'
const faceMode = ref('login') // 'login' | 'register'

function handleFaceSuccess(data) {
  emit('login-success')
}

function handleFaceCancel() {
  // 如果取消注册，回到登录模式
  if (faceMode.value === 'register') {
    faceMode.value = 'login'
  }
}

function switchToRegister() {
  faceMode.value = 'register'
}

function switchToFace() {
  faceMode.value = 'login'
  loginMode.value = 'face'
}

// 简单登录（原二维码模式）
const loading = ref(false)

async function handleSimpleLogin() {
  loading.value = true
  try {
    await fetch('/api/auth/qrcode', { method: 'POST' })
    await fetch('/api/auth/scan/test', { method: 'POST' }).catch(() => {})
    await fetch('/api/auth/confirm/test', { method: 'POST' }).catch(() => {})
  } catch { /* ignore */ }
  emit('login-success')
}
</script>

<template>
  <div class="login-page">
    <div class="login-container">
      <!-- 左侧品牌区 -->
      <div class="login-brand">
        <div class="brand-icon">🏢</div>
        <h1 class="brand-title">人才梯队平台</h1>
        <p class="brand-subtitle">HR 智能驾驶舱</p>
        <p class="brand-desc">全方位人才管理 · 继任规划 · 风险预警</p>
      </div>

      <!-- 右侧操作区 -->
      <div class="login-action">
        <!-- 方式选择标签 -->
        <div class="mode-tabs">
          <button
            :class="['tab-btn', { active: loginMode === 'face' }]"
            @click="loginMode = 'face'"
          >
            😊 扫脸登录
          </button>
          <button
            :class="['tab-btn', { active: loginMode === 'simple' }]"
            @click="loginMode = 'simple'"
          >
            🔑 快捷进入
          </button>
        </div>

        <!-- 扫脸模式 -->
        <div v-if="loginMode === 'face'" class="face-section">
          <!-- 登录/注册切换 -->
          <div class="face-tabs">
            <button
              :class="['tab-sm', { active: faceMode === 'login' }]"
              @click="switchToFace"
            >
              扫脸登录
            </button>
            <button
              :class="['tab-sm', { active: faceMode === 'register' }]"
              @click="switchToRegister"
            >
              扫脸注册
            </button>
          </div>

          <!-- 提示文字 -->
          <p class="face-hint">
            {{ faceMode === 'login' ? '面对摄像头完成扫脸登录' : '首次使用请先注册人脸信息' }}
          </p>

          <!-- 摄像头组件 -->
          <FaceCamera
            :mode="faceMode"
            @success="handleFaceSuccess"
            @error="handleFaceCancel"
            @cancel="handleFaceCancel"
          />
        </div>

        <!-- 简单登录模式 -->
        <div v-else class="simple-section">
          <h2>欢迎回来</h2>
          <p class="action-hint">点击下方按钮进入系统</p>
          <button class="login-btn" :disabled="loading" @click="handleSimpleLogin">
            {{ loading ? '登录中...' : '🚀 进入系统' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0f0c29 0%, #1a1a4e 50%, #24243e 100%);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.login-container {
  display: flex;
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.5);
  width: 780px;
  min-height: 520px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.login-brand {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px;
  background: linear-gradient(160deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.08));
  text-align: center;
}

.brand-icon { font-size: 64px; margin-bottom: 16px; }

.brand-title {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  margin: 0 0 8px;
}

.brand-subtitle {
  font-size: 16px;
  color: rgba(255,255,255,0.6);
  margin: 0 0 4px;
  letter-spacing: 2px;
}

.brand-desc {
  font-size: 13px;
  color: rgba(255,255,255,0.4);
  margin: 12px 0 0;
}

.login-action {
  width: 380px;
  padding: 32px 28px;
  display: flex;
  flex-direction: column;
  align-items: center;
  overflow-y: auto;
  max-height: 560px;
}

/* ── 登录方式标签 ── */
.mode-tabs {
  display: flex;
  gap: 4px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  padding: 3px;
  margin-bottom: 16px;
  width: 100%;
}

.tab-btn {
  flex: 1;
  padding: 8px 12px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: rgba(255, 255, 255, 0.5);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn.active {
  background: rgba(99, 102, 241, 0.25);
  color: #fff;
}

.tab-btn:hover:not(.active) {
  color: rgba(255, 255, 255, 0.8);
}

/* ── 扫脸区域 ── */
.face-section {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.face-tabs {
  display: flex;
  gap: 8px;
}

.tab-sm {
  padding: 6px 18px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 20px;
  background: transparent;
  color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-sm.active {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border-color: transparent;
  color: #fff;
}

.tab-sm:hover:not(.active) {
  color: rgba(255, 255, 255, 0.8);
  border-color: rgba(255, 255, 255, 0.3);
}

.face-hint {
  color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
  margin: 0;
  text-align: center;
}

/* ── 简单登录 ── */
.simple-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 40px 0;
}

.simple-section h2 {
  color: #fff;
  margin: 0;
  font-size: 22px;
  font-weight: 600;
}

.action-hint {
  color: rgba(255,255,255,0.5);
  margin: 0;
  font-size: 14px;
}

.login-btn {
  margin-top: 12px;
  padding: 14px 48px;
  border: none;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.login-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(99, 102, 241, 0.3);
}

.login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}
</style>