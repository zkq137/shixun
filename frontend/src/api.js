export async function fetchJson(url) {
  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`)
  }

  return response.json()
}

export async function getDashboardData() {
  const [health, overview, nineBox, succession, risks, training] = await Promise.all([
    fetchJson('/api/health'),
    fetchJson('/api/overview'),
    fetchJson('/api/nine-box'),
    fetchJson('/api/succession'),
    fetchJson('/api/risks'),
    fetchJson('/api/training-plans')
  ])

  return {
    health,
    overview,
    nineBox,
    succession,
    risks,
    training
  }
}

export async function getRiskAlerts() {
  return fetchJson('/api/risks')
}

export async function getRiskOverview() {
  return fetchJson('/api/risk-overview')
}

export async function getRiskEmployees(level) {
  const query = level && level !== '全部'
    ? `?level=${encodeURIComponent(level)}`
    : ''
  return fetchJson(`/api/risk-employees${query}`)
}

export async function getRiskEmployeeDetail(employeeId) {
  return fetchJson(`/api/risk-employees/${encodeURIComponent(employeeId)}`)
}

export async function getDifyStatus() {
  return fetchJson('/api/dify/status')
}

export async function generateRiskIntervention(payload) {
  const response = await fetch('/api/risk-intervention', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  const data = await response.json()
  if (!response.ok) {
    throw new Error(data.error || `请求失败: ${response.status}`)
  }

  return data
}
