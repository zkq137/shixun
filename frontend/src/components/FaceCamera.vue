<script setup>
/**
 * FaceCamera.vue — 摄像头人脸采集组件
 * 支持扫脸登录和注册两种模式
 */
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  mode: {
    type: String,
    default: 'login', // 'login' | 'register'
  },
})

const emit = defineEmits(['success', 'error', 'cancel'])

// ── 状态 ──
const videoRef = ref(null)
const canvasRef = ref(null)
const capturedImage = ref(null) // base64
const capturedFrames = ref([]) // 多帧（注册模式）
const isCapturing = ref(false)
const isProcessing = ref(false)
const statusMessage = ref('')
const statusType = ref('') // 'info' | 'success' | 'error'
const username = ref('')
const hasCamera = ref(true)

let mediaStream = null
let captureTimer = null

// ── 生命周期 ──
onMounted(() => {
  startCamera()
})

onUnmounted(() => {
  stopCamera()
  if (captureTimer) clearInterval(captureTimer)
})

// ── 摄像头控制 ──
async function startCamera() {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 640 },
        height: { ideal: 480 },
        facingMode: 'user',
      },
      audio: false,
    })
    if (videoRef.value) {
      videoRef.value.srcObject = mediaStream
    }
    hasCamera.value = true
  } catch (err) {
    console.error('摄像头启动失败:', err)
    hasCamera.value = false
    setStatus('无法访问摄像头，请确保已授予摄像头权限', 'error')
  }
}

function stopCamera() {
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop())
    mediaStream = null
  }
}

// ── 拍照 ──
function capture() {
  const video = videoRef.value
  const canvas = canvasRef.value
  if (!video || !canvas) return

  if (props.mode === 'register') {
    // 注册模式：连拍 3 帧，取最佳
    captureMultiFrame(video, canvas)
  } else {
    // 登录模式：单帧
    captureSingle(video, canvas)
  }
}

function captureSingle(video, canvas, setStatusMsg = true) {
  const ctx = canvas.getContext('2d')
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  ctx.drawImage(video, 0, 0)
  capturedImage.value = canvas.toDataURL('image/jpeg', 0.9)
  isCapturing.value = true
  if (setStatusMsg) {
    setStatus('照片已拍摄，点击"确认"提交', 'info')
  }
}

function captureMultiFrame(video, canvas) {
  const ctx = canvas.getContext('2d')
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight

  const frames = []
  // 连拍 3 帧，间隔 200ms
  for (let i = 0; i < 3; i++) {
    ctx.drawImage(video, 0, 0)
    frames.push(canvas.toDataURL('image/jpeg', 0.85))
    // 等待一帧
    const t0 = Date.now()
    while (Date.now() - t0 < 200) { /* busy wait for frame interval */ }
  }

  // 取中间帧作为展示，发送全部 3 帧到后端
  capturedFrames.value = frames
  capturedImage.value = frames[1] // 中间帧预览
  isCapturing.value = true
  setStatus('已拍摄 3 帧（提高识别精度），点击确认提交', 'info')
}

function retake() {
  capturedImage.value = null
  capturedFrames.value = []
  isCapturing.value = false
  setStatus('', '')
}

// ── 提交 ──
async function submit() {
  if (!capturedImage.value) return
  isProcessing.value = true
  setStatus('正在处理...', 'info')

  try {
    if (props.mode === 'register') {
      await handleRegister()
    } else {
      await handleLogin()
    }
  } catch (err) {
    setStatus(err.message || '请求失败', 'error')
  } finally {
    isProcessing.value = false
  }
}

async function handleLogin() {
  const resp = await fetch('/api/face/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image: capturedImage.value }),
  })
  const data = await resp.json()

  if (resp.ok) {
    setStatus(`✅ 登录成功！欢迎 ${data.username}`, 'success')
    // 存储登录状态
    localStorage.setItem('shixun_logged_in', 'true')
    localStorage.setItem('shixun_face_user', data.username)
    setTimeout(() => emit('success', data), 1000)
  } else {
    setStatus(data.error || '登录失败', 'error')
  }
}

async function handleRegister() {
  if (!username.value.trim()) {
    setStatus('请输入用户名', 'error')
    isProcessing.value = false
    return
  }

  // 发送多帧（3帧）让后端综合提取特征
  const images = capturedFrames.length > 0 ? capturedFrames : [capturedImage.value]

  const resp = await fetch('/api/face/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: username.value.trim(),
      images: images,       // 多帧数组
      image: images[0],     // 兼容单帧
    }),
  })
  const data = await resp.json()

  if (resp.ok) {
    setStatus('✅ 人脸注册成功！', 'success')
    setTimeout(() => emit('success', data), 1000)
  } else {
    setStatus(data.error || '注册失败', 'error')
  }
}

function setStatus(msg, type) {
  statusMessage.value = msg
  statusType.value = type
}

function goBack() {
  stopCamera()
  emit('cancel')
}
</script>

<template>
  <div class="face-camera">
    <!-- 状态提示 -->
    <div v-if="statusMessage" :class="['status-bar', statusType]">
      {{ statusMessage }}
    </div>

    <!-- 摄像头不可用 -->
    <div v-if="!hasCamera" class="no-camera">
      <p>📷 无法访问摄像头</p>
      <p class="hint">请确保：</p>
      <ul>
        <li>浏览器已授予摄像头权限</li>
        <li>没有其他应用占用摄像头</li>
        <li>使用 HTTPS 或 localhost 访问</li>
      </ul>
      <button class="btn btn-secondary" @click="goBack">返回</button>
    </div>

    <!-- 摄像头画面 -->
    <div v-else class="camera-container">
      <!-- 注册模式：用户名输入（拍照前就显示） -->
      <div v-if="mode === 'register'" class="username-input">
        <label>用户名：</label>
        <input
          v-model="username"
          type="text"
          placeholder="请输入用户名（必填）"
          maxlength="50"
          :disabled="isProcessing"
        />
      </div>

      <!-- 视频预览（始终渲染，用 v-show 切换显隐，避免摄像头断开） -->
      <div v-show="!isCapturing" class="preview-wrapper">
        <video ref="videoRef" autoplay playsinline class="video-preview"></video>
        <div class="face-hint">
          <span class="hint-icon">😊</span>
          <span>请将面部对准摄像头</span>
        </div>
        <div class="camera-actions">
          <button class="btn btn-primary" @click="capture">
            📸 拍照
          </button>
          <button class="btn btn-secondary" @click="goBack">返回</button>
        </div>
      </div>

      <!-- 隐藏 canvas（始终渲染，供 capture 函数使用） -->
      <canvas ref="canvasRef" style="display:none"></canvas>

      <!-- 已拍照预览 -->
      <div v-show="isCapturing" class="capture-wrapper">
        <img v-if="capturedImage" :src="capturedImage" class="captured-image" />
        <div class="camera-actions">
          <button
            class="btn btn-primary"
            :disabled="isProcessing || (mode === 'register' && !username.trim())"
            @click="submit"
          >
            {{ isProcessing ? '处理中...' : mode === 'register' ? '✅ 确认注册' : '✅ 确认登录' }}
          </button>
          <button class="btn btn-secondary" :disabled="isProcessing" @click="retake">
            🔄 重拍
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.face-camera {
  width: 100%;
  max-width: 520px;
  margin: 0 auto;
}

.status-bar {
  padding: 10px 16px;
  border-radius: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  text-align: center;
  animation: fadeIn 0.3s;
}
.status-bar.info {
  background: rgba(99, 102, 241, 0.15);
  color: #a5b4fc;
}
.status-bar.success {
  background: rgba(34, 197, 94, 0.15);
  color: #86efac;
}
.status-bar.error {
  background: rgba(239, 68, 68, 0.15);
  color: #fca5a5;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-5px); }
  to { opacity: 1; transform: translateY(0); }
}

.no-camera {
  text-align: center;
  padding: 40px 20px;
}
.no-camera p { color: #fff; font-size: 18px; margin: 0 0 12px; }
.no-camera .hint { font-size: 14px; color: rgba(255,255,255,0.5); }
.no-camera ul {
  list-style: none;
  padding: 0;
  color: rgba(255,255,255,0.6);
  font-size: 13px;
  margin: 8px 0 20px;
}
.no-camera ul li { padding: 4px 0; }

.camera-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.preview-wrapper,
.capture-wrapper {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.video-preview,
.captured-image {
  width: 100%;
  max-width: 480px;
  border-radius: 12px;
  background: #000;
  border: 2px solid rgba(255, 255, 255, 0.1);
}

.face-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(255, 255, 255, 0.6);
  font-size: 14px;
}
.hint-icon { font-size: 24px; }

.camera-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: center;
}

.btn {
  padding: 10px 24px;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-primary {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
}
.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
}
.btn-secondary {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.15);
}
.btn-secondary:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.18);
}

.username-input {
  width: 100%;
  max-width: 360px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.username-input label {
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
}
.username-input input {
  padding: 10px 14px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  font-size: 15px;
  outline: none;
  transition: border-color 0.2s;
}
.username-input input:focus {
  border-color: #6366f1;
}
.username-input input::placeholder {
  color: rgba(255, 255, 255, 0.3);
}
</style>
