<script setup>
import { ref } from 'vue'
import { fetchJson } from '../api'

const employeeNo = ref('')
const loading = ref(false)
const error = ref('')
const employee = ref(null)

async function search() {
  const no = employeeNo.value.trim()
  if (!no) return

  loading.value = true
  error.value = ''
  employee.value = null

  try {
    const res = await fetch(`/api/employees/${no}`)
    const data = await res.json()
    if (!res.ok || data.error) {
      error.value = data.error || '查询失败'
    } else {
      employee.value = data
    }
  } catch (e) {
    error.value = '网络错误：' + e.message
  } finally {
    loading.value = false
  }
}

function formatSalary(v) {
  if (v == null) return '--'
  return `¥${v.toLocaleString()}`
}

function riskClass(level) {
  if (!level) return ''
  if (level.includes('高')) return 'risk-high'
  if (level.includes('中')) return 'risk-mid'
  return 'risk-low'
}
</script>

<template>
  <div class="employee-search">
    <!-- 搜索栏 -->
    <div class="search-bar">
      <input
        v-model="employeeNo"
        type="text"
        placeholder="请输入员工工号，如 E70014679"
        class="search-input"
        @keyup.enter="search"
      />
      <button class="search-btn" @click="search" :disabled="loading">
        {{ loading ? '查询中...' : '🔍 查询' }}
      </button>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="panel error">{{ error }}</div>

    <!-- 加载中 -->
    <div v-if="loading" class="panel loading-state">⏳ 查询中...</div>

    <!-- 员工信息卡片 -->
    <template v-if="employee">
      <!-- 基本信息 -->
      <section class="panel">
        <h2>📋 基本信息</h2>
        <div class="info-grid">
          <div><label>工号</label><span>{{ employee.employeeNo }}</span></div>
          <div><label>姓名</label><span class="name">{{ employee.name }}</span></div>
          <div><label>部门</label><span>{{ employee.department }}</span></div>
          <div><label>岗位</label><span>{{ employee.position }}</span></div>
          <div><label>职级</label><span>{{ employee.jobLevel }}</span></div>
          <div><label>职等</label><span>{{ employee.rankName }}</span></div>
          <div><label>上级工号</label><span>{{ employee.managerNo || '无' }}</span></div>
        </div>
      </section>

      <!-- 画像信息 -->
      <section class="panel" v-if="employee.profile">
        <h2>👤 员工画像</h2>
        <div class="info-grid">
          <div><label>年龄</label><span>{{ employee.profile.age }} 岁</span></div>
          <div><label>性别</label><span>{{ employee.profile.gender }}</span></div>
          <div><label>司龄</label><span>{{ employee.profile.tenureYears }} 年</span></div>
          <div><label>基本年薪</label><span>{{ formatSalary(employee.profile.baseSalary) }}</span></div>
          <div><label>薪酬系数</label><span>{{ employee.profile.compensationFactor }}</span></div>
          <div><label>办公方式</label><span>{{ employee.profile.workMode }}</span></div>
        </div>
      </section>

      <!-- 技能标签 -->
      <section class="panel" v-if="employee.skills && employee.skills.length">
        <h2>🛠️ 技能标签</h2>
        <div class="tags">
          <span v-for="s in employee.skills" :key="s" class="tag">{{ s }}</span>
        </div>
      </section>

      <!-- 培训记录 -->
      <section class="panel" v-if="employee.trainings && employee.trainings.length">
        <h2>📚 培训记录</h2>
        <ul class="list">
          <li v-for="t in employee.trainings" :key="t.name">
            <h4>{{ t.name }}</h4>
          </li>
        </ul>
      </section>

      <!-- 人才评估 -->
      <section class="panel" v-if="employee.assessment">
        <h2>⭐ 人才评估</h2>
        <div class="info-grid">
          <div><label>绩效评分</label><span>{{ employee.assessment.performanceScore }}</span></div>
          <div><label>潜力评分</label><span>{{ employee.assessment.potentialScore }}</span></div>
          <div><label>潜力等级</label><span>{{ employee.assessment.potentialLevel }}</span></div>
          <div><label>人才标签</label><span class="tag">{{ employee.assessment.talentTag }}</span></div>
        </div>
      </section>

      <!-- 流失风险 -->
      <section class="panel" v-if="employee.risk">
        <h2>⚠️ 流失风险</h2>
        <div class="info-grid">
          <div><label>风险分</label><span>{{ employee.risk.riskScore }}</span></div>
          <div><label>风险等级</label><span :class="['risk-tag', riskClass(employee.risk.riskLevel)]">{{ employee.risk.riskLevel }}</span></div>
        </div>
      </section>

      <!-- 岗位画像 -->
      <section class="panel" v-if="employee.positionProfile">
        <h2>🎯 岗位画像</h2>
        <div class="info-grid">
          <div><label>岗位类型</label><span>{{ employee.positionProfile.positionType }}</span></div>
          <div><label>是否管理岗</label><span>{{ employee.positionProfile.isManager === '是' ? '是' : '否' }}</span></div>
          <div><label>绩效要求</label><span>{{ employee.positionProfile.performanceRequirement || '--' }}</span></div>
          <div><label>司龄要求</label><span>{{ employee.positionProfile.tenureRequirement || '--' }}</span></div>
          <div><label>办公方式要求</label><span>{{ employee.positionProfile.workModeRequirement || '--' }}</span></div>
          <div v-if="employee.positionProfile.fitDescription" class="full-width">
            <label>适配描述</label><span>{{ employee.positionProfile.fitDescription }}</span>
          </div>
        </div>
        <div v-if="employee.positionProfile.coreSkills.length" style="margin-top:12px">
          <label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:6px">核心技能</label>
          <div class="tags">
            <span v-for="s in employee.positionProfile.coreSkills" :key="s" class="tag tag-core">{{ s }}</span>
          </div>
        </div>
        <div v-if="employee.positionProfile.bonusSkills.length" style="margin-top:8px">
          <label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:6px">加分技能</label>
          <div class="tags">
            <span v-for="s in employee.positionProfile.bonusSkills" :key="s" class="tag tag-bonus">{{ s }}</span>
          </div>
        </div>
        <div v-if="employee.positionProfile.requiredTraining.length" style="margin-top:8px">
          <label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:6px">必修培训</label>
          <div class="tags">
            <span v-for="t in employee.positionProfile.requiredTraining" :key="t" class="tag tag-training">{{ t }}</span>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.employee-search {
  max-width: 800px;
}

.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.search-input {
  flex: 1;
  padding: 12px 16px;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  font-size: 15px;
  outline: none;
  transition: border-color 0.2s;
  background: #fff;
}

.search-input:focus {
  border-color: #14b8a6;
}

.search-btn {
  padding: 12px 24px;
  border: 0;
  background: #14b8a6;
  color: #fff;
  border-radius: 10px;
  font-size: 15px;
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}

.search-btn:hover { background: #0d9488; }
.search-btn:disabled { background: #94a3b8; cursor: not-allowed; }

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.info-grid div {
  padding: 10px 14px;
  background: #f8fafc;
  border-radius: 8px;
}

.info-grid div.full-width {
  grid-column: 1 / -1;
}

.info-grid label {
  display: block;
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 4px;
}

.info-grid span {
  font-size: 15px;
  font-weight: 500;
}

.name {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag {
  display: inline-block;
  padding: 4px 12px;
  background: #ecfdf5;
  color: #065f46;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 500;
}

.status-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 13px;
}

.status-tag.active { background: #dcfce7; color: #166534; }
.status-tag.inactive { background: #fee2e2; color: #991b1b; }

/* 复用全局 panel/list 样式 */
.panel {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 24px;
  margin-bottom: 20px;
}

.panel h2 {
  margin: 0 0 16px;
  font-size: 18px;
  font-weight: 600;
}

.loading-state {
  text-align: center;
  padding: 60px;
  font-size: 18px;
  color: #64748b;
}

.error {
  border-color: #fca5a5;
  color: #b91c1c;
}

.list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 8px;
}

.list li {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px;
}

.list h4 { margin: 0 0 4px; font-size: 15px; }
.list p { margin: 0; color: #64748b; font-size: 13px; }

.risk-tag { font-size: 13px; padding: 2px 10px; border-radius: 999px; font-weight: 600; }
.risk-high { color: #dc2626; }
.risk-mid { color: #d97706; }
.risk-low { color: #16a34a; }

.tag-core { background: #dbeafe; color: #1e40af; }
.tag-bonus { background: #fef3c7; color: #92400e; }
.tag-training { background: #ede9fe; color: #5b21b6; }
</style>
