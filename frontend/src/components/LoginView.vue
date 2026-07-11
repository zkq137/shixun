<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import QRCode from 'qrcode'

const emit = defineEmits(['login-success'])

const token = ref('')
const qrDataUrl = ref('')
const loginMode = ref('demo')
const status = ref('loading')
const statusText = ref('正在准备...')
const pollTimer = ref(null)

function startWeChatLogin() {
  loginMode.value = 'wechat'
  status.value = 'pending'
  statusText.value = '请在微信中扫码登录'
  fetch('/api/auth/wechat/url')
    .then(function(r) { return r.json() })
    .then(function(data) {
      QRCode.toDataURL(data.url, {
        width: 280,
        margin: 2,
        color: { dark: '#07c160', light: '#ffffff' }
      }).then(function(url) {
        qrDataUrl.value = url
        return fetch('/api/auth/qrcode', { method: 'POST' })
      }).then(function(r) { return r.json() })
      .then(function(d) {
        token.value = d.token
        startPolling()
      })
    })
    .catch(function() {
      statusText.value = '获取微信授权失败，请重试'
      status.value = 'error'
    })
}

async function startDemoLogin() {
  loginMode.value = 'demo'
  status.value = 'loading'
  statusText.value = '正在生成二维码...'
  try {
    const resp = await fetch('/api/auth/qrcode', { method: 'POST' })
    const data = await resp.json()
    token.value = data.token
    const loginUrl = window.location.origin + '/login?token=' + data.token
    qrDataUrl.value = await QRCode.toDataURL(loginUrl, {
      width: 280,
      margin: 2,
      color: { dark: '#1a1a2e', light: '#ffffff' }
    })
    status.value = 'pending'
    statusText.value = '请使用手机扫码登录'
    startPolling()
  } catch (_e) {
    statusText.value = '生成二维码失败，请重试'
    status.value = 'error'
  }
}

function switchToWeChat() {
  status.value = 'loading'
  qrDataUrl.value = ''
  startWeChatLogin()
}

function startPolling() {
  stopPolling()
  pollTimer.value = setInterval(async function() {
    try {
      const resp = await fetch('/api/auth/status/' + token.value)
      const data = await resp.json()
      if (data.status === 'scanned') {
        status.value = 'scanned'
        statusText.value = '手机已扫码，请在手机上确认登录'
        stopPolling()
      } else if (data.status === 'confirmed') {
        onLoginSuccess()
      } else if (data.status === 'expired') {
        status.value = 'expired'
        statusText.value = '二维码已过期，请刷新重试'
        stopPolling()
      }
    } catch (_e) { /* ignore */ }
  }, 1500)
}

function stopPolling() {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

async function simulateScan() {
  try {
    const resp = await fetch('/api/auth/scan/' + token.value, { method: 'POST' })
    if (resp.ok) {
      status.value = 'scanned'
      statusText.value = '手机已扫码，请在手机上确认登录'
      stopPolling()
    }
  } catch (_e) { /* ignore */ }
}

async function simulateConfirm() {
  try {
    const resp = await fetch('/api/auth/confirm/' + token.value, { method: 'POST' })
    if (resp.ok) onLoginSuccess()
  } catch (_e) { /* ignore */ }
}

async function checkWeChatToken(loginToken) {
  try {
    const resp = await fetch('/api/auth/wechat/user/' + loginToken)
    if (resp.ok) {
      token.value = loginToken
      onLoginSuccess()
      return true
    }
  } catch (_e) { /* ignore */ }
  return false
}

function onLoginSuccess() {
  status.value = 'confirmed'
  statusText.value = '登录成功！'
  stopPolling()
  setTimeout(function() { emit('login-success') }, 600)
}

onMounted(function() {
  const params = new URLSearchParams(window.location.search)
  const loginToken = params.get('login_token')
  if (loginToken) {
    checkWeChatToken(loginToken)
    window.history.replaceState({}, '', window.location.pathname)
    return
  }
  const handler = function(event) {
    if (event.origin !== window.location.origin) return
    if (event.data && event.data.type === 'WECHAT_LOGIN_SUCCESS') {
      token.value = event.data.token
      onLoginSuccess()
    }
  }
  window.addEventListener('message', handler)
  // 初始显示模式选择，不自动启动
  stopPolling()
  onUnmounted(function() {
    window.removeEventListener('message', handler)
  })
})

onUnmounted(function() {
  stopPolling()
})
</script>

<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-brand">
        <div class="brand-content">
          <div class="brand-icon">&#x1F3E2;</div>
          <h1 class="brand-title">人才梯队平台</h1>
          <p class="brand-subtitle">HR 智能驾驶舱</p>
          <p class="brand-desc">全方位人才管理 · 继任规划 · 风险预警</p>
        </div>
      </div>
      <div class="login-qr-section">
        <div v-if="(status === 'loading') && !qrDataUrl" class="mode-select">
          <div class="mode-card wechat" @click="startWeChatLogin">
            <div class="mode-icon">&#x1F49A;</div>
            <h3>微信扫码登录</h3>
            <p>使用企业微信 / 个人微信<br/>扫码安全登录</p>
          </div>
          <div class="mode-divider"><span>或</span></div>
          <div class="mode-card demo" @click="startDemoLogin">
            <div class="mode-icon">&#x1F9EA;</div>
            <h3>演示模式</h3>
            <p>无微信凭据时<br/>点击按钮模拟登录</p>
          </div>
        </div>
        <div v-else class="qr-card">
          <div class="qr-header">
            <h2>
              <span v-if="loginMode === 'wechat'">&#x1F49A; 微信扫码</span>
              <span v-else>&#x1F4F1; 扫码登录</span>
            </h2>
            <p class="qr-hint">{{ statusText }}</p>
          </div>
          <div class="qr-display" :class="{ 'qr-expired': status === 'expired' }">
            <img v-if="qrDataUrl" :src="qrDataUrl" alt="登录二维码"/>
            <div v-else class="qr-loading"><div class="spinner"></div></div>
            <div v-if="status === 'expired'" class="qr-overlay">
              <p>二维码已过期</p>
              <button class="btn btn-primary" @click="startDemoLogin">重新生成</button>
            </div>
          </div>
          <div class="qr-status">
            <div v-if="status === 'pending'" class="status-dot pending"></div>
            <div v-else-if="status === 'scanned'" class="status-dot scanning"></div>
            <div v-else-if="status === 'confirmed'" class="status-dot success"></div>
            <span>{{ statusText }}</span>
          </div>
          <div v-if="loginMode === 'wechat' && status === 'pending'" class="wechat-tip">
            <p>1. 打开手机微信「扫一扫」</p>
            <p>2. 扫描屏幕二维码</p>
            <p>3. 在手机上确认登录</p>
          </div>
          <div v-if="loginMode === 'demo'" class="demo-section">
            <p class="demo-label">&#x1F4F1; 演示流程（点击模拟手机操作）</p>
            <div class="demo-actions">
              <button v-if="status === 'pending'" class="btn btn-outline" @click="simulateScan">&#x1F4F8; 模拟扫码</button>
              <button v-if="status === 'scanned'" class="btn btn-primary" @click="simulateConfirm">&#x2705; 模拟确认登录</button>
              <button v-if="status === 'expired'" class="btn btn-primary" @click="startDemoLogin">&#x1F504; 重新生成</button>
            </div>
          </div>
          <div class="qr-footer">
            <p v-if="loginMode === 'wechat'">未注册？扫码后按指引开通</p>
            <p v-else><a href="#" @click.prevent="switchToWeChat">切换到微信登录</a></p>
          </div>
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
  width: 860px;
  min-height: 520px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.login-brand {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  background: linear-gradient(160deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.08));
}
.brand-content { text-align: center; }
.brand-icon { font-size: 64px; margin-bottom: 16px; }
.brand-title { font-size: 28px; font-weight: 700; color: #fff; margin: 0 0 8px; }
.brand-subtitle { font-size: 16px; color: rgba(255,255,255,0.6); margin: 0 0 4px; letter-spacing: 2px; }
.brand-desc { font-size: 13px; color: rgba(255,255,255,0.4); margin: 12px 0 0; }
.login-qr-section {
  width: 420px;
  padding: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.mode-select {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.mode-card {
  text-align: center;
  padding: 28px 20px;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.3s;
  border: 1px solid rgba(255,255,255,0.1);
}
.mode-card.wechat {
  background: linear-gradient(135deg, rgba(7, 193, 96, 0.15), rgba(7, 193, 96, 0.05));
}
.mode-card.wechat:hover {
  background: linear-gradient(135deg, rgba(7, 193, 96, 0.25), rgba(7, 193, 96, 0.1));
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(7, 193, 96, 0.2);
}
.mode-card.demo {
  background: rgba(255,255,255,0.04);
}
.mode-card.demo:hover {
  background: rgba(255,255,255,0.08);
  transform: translateY(-2px);
}
.mode-icon { font-size: 40px; margin-bottom: 8px; }
.mode-card h3 { margin: 0 0 6px; font-size: 16px; font-weight: 600; color: #fff; }
.mode-card p { margin: 0; font-size: 13px; color: rgba(255,255,255,0.45); line-height: 1.6; }
.mode-card.wechat h3 { color: #07c160; }
.mode-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  color: rgba(255,255,255,0.2);
  font-size: 12px;
}
.mode-divider::before,
.mode-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: rgba(255,255,255,0.08);
}
.qr-card { text-align: center; width: 100%; }
.qr-header h2 { font-size: 22px; font-weight: 600; color: #fff; margin: 0 0 6px; }
.qr-hint { font-size: 13px; color: rgba(255,255,255,0.5); margin: 0 0 20px; }
.qr-display {
  position: relative;
  width: 220px;
  height: 220px;
  margin: 0 auto 16px;
  background: #fff;
  border-radius: 16px;
  padding: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s;
}
.qr-display img { width: 100%; height: 100%; object-fit: contain; border-radius: 8px; }
.qr-display.qr-expired { opacity: 0.6; }
.qr-loading { display: flex; align-items: center; justify-content: center; }
.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(99, 102, 241, 0.2);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.qr-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255,255,255,0.92);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}
.qr-overlay p { color: #ef4444; font-size: 14px; font-weight: 500; }
.qr-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 13px;
  color: rgba(255,255,255,0.6);
  margin-bottom: 16px;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.status-dot.pending { background: #6366f1; animation: pulse 2s infinite; }
.status-dot.scanning { background: #f59e0b; animation: pulse 1s infinite; }
.status-dot.success { background: #22c55e; }
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.3); }
}
.wechat-tip {
  background: rgba(7, 193, 96, 0.08);
  border: 1px solid rgba(7, 193, 96, 0.15);
  border-radius: 12px;
  padding: 12px 16px;
  margin-bottom: 16px;
  text-align: left;
}
.wechat-tip p { margin: 0 0 4px; font-size: 13px; color: rgba(255,255,255,0.6); }
.wechat-tip p:last-child { margin-bottom: 0; }
.wechat-tip p::before { content: '• '; color: #07c160; }
.demo-section {
  background: rgba(255,255,255,0.05);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  border: 1px dashed rgba(255,255,255,0.1);
}
.demo-label { font-size: 12px; color: rgba(255,255,255,0.4); margin: 0 0 10px; }
.demo-actions { display: flex; justify-content: center; gap: 10px; }
.btn {
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}
.btn-primary {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
}
.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(99,102,241,0.4); }
.btn-outline {
  background: transparent;
  color: rgba(255,255,255,0.7);
  border: 1px solid rgba(255,255,255,0.2);
}
.btn-outline:hover { background: rgba(255,255,255,0.08); color: #fff; }
.qr-footer {
  border-top: 1px solid rgba(255,255,255,0.06);
  padding-top: 16px;
}
.qr-footer p { font-size: 12px; color: rgba(255,255,255,0.3); margin: 0; }
.qr-footer a { color: #6366f1; text-decoration: none; }
.qr-footer a:hover { text-decoration: underline; }
</style>