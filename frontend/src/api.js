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

export async function getRiskEmployees(params = {}) {
  const search = new URLSearchParams()

  if (params.level && params.level !== '全部') {
    search.set('level', params.level)
  }
  if (params.keyword) {
    search.set('keyword', params.keyword)
  }
  if (params.page) {
    search.set('page', params.page)
  }
  if (params.pageSize) {
    search.set('pageSize', params.pageSize)
  }

  const query = search.toString()
  return fetchJson(`/api/risk-employees${query ? `?${query}` : ''}`)
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
