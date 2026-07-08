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
