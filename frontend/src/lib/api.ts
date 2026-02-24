const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${endpoint}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  })
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

// Health
export const getHealth = () => fetchAPI<import("./types").HealthStatus>("/api/health")

// Portfolio
export const getPositions = (status?: string) =>
  fetchAPI<import("./types").PortfolioPosition[]>(`/api/portfolio/positions${status ? `?status=${status}` : ""}`)
export const getPnL = () => fetchAPI<import("./types").DailySnapshot[]>("/api/portfolio/pnl")
export const getPortfolioSummary = () => fetchAPI<import("./types").PortfolioSummary>("/api/portfolio/summary")

// Recommendations
export const getRecommendations = (status?: string) =>
  fetchAPI<import("./types").TradeRecommendation[]>(`/api/recommendations${status ? `?status=${status}` : ""}`)
export const reviewRecommendation = (id: string, action: string, note: string) =>
  fetchAPI(`/api/recommendations/${id}/review`, {
    method: "POST",
    body: JSON.stringify({ action, note }),
  })

// Journal
export const getJournal = (params?: { ticker?: string; action?: string; page?: number }) => {
  const searchParams = new URLSearchParams()
  if (params?.ticker) searchParams.set("ticker", params.ticker)
  if (params?.action) searchParams.set("action", params.action)
  if (params?.page) searchParams.set("page", params.page.toString())
  const qs = searchParams.toString()
  return fetchAPI<import("./types").DecisionJournalEntry[]>(`/api/journal${qs ? `?${qs}` : ""}`)
}
export const getJournalEntry = (id: string) =>
  fetchAPI<import("./types").DecisionJournalEntry>(`/api/journal/${id}`)

// Debates
export const getDebates = () => fetchAPI<import("./types").DebateTranscript[]>("/api/debates")
export const getDebate = (pipelineRunId: string) =>
  fetchAPI<import("./types").DebateTranscript>(`/api/debates/${pipelineRunId}`)

// Jury
export const getJuryVotes = (pipelineRunId: string) =>
  fetchAPI<import("./types").JuryVote[]>(`/api/jury/${pipelineRunId}`)
export const getJuryStats = () => fetchAPI<import("./types").JuryStats>("/api/jury/stats")

// Overrides
export const getOverrides = (status?: string) =>
  fetchAPI<import("./types").VetoOverride[]>(`/api/overrides${status ? `?status=${status}` : ""}`)
export const createOverride = (data: { ticker: string; override_reason: string; overridden_by: string }) =>
  fetchAPI("/api/overrides", { method: "POST", body: JSON.stringify(data) })

// Alerts
export const getAlerts = (params?: { severity?: string; acknowledged?: boolean }) => {
  const searchParams = new URLSearchParams()
  if (params?.severity) searchParams.set("severity", params.severity)
  if (params?.acknowledged !== undefined) searchParams.set("acknowledged", params.acknowledged.toString())
  const qs = searchParams.toString()
  return fetchAPI<import("./types").RiskAlert[]>(`/api/alerts${qs ? `?${qs}` : ""}`)
}
export const getStreak = () => fetchAPI<import("./types").ConsecutiveLossTracker>("/api/alerts/streak")
export const acknowledgeAlert = (id: string) =>
  fetchAPI(`/api/alerts/${id}/acknowledge`, { method: "POST" })

// Bias
export const getBiasMetrics = () => fetchAPI<import("./types").BiasMetric>("/api/bias/metrics")
export const getBiasHistory = () => fetchAPI<import("./types").BiasMetric[]>("/api/bias/history")

// Screening
export const getLatestScreening = () => fetchAPI<import("./types").ScreeningRun>("/api/screening/latest")
export const getScreeningHistory = () => fetchAPI<import("./types").ScreeningRun[]>("/api/screening/history")

// Settings
export const getSettings = () =>
  fetchAPI<{ settings: import("./types").SystemSetting[]; api_status: Record<string, { connected: boolean; latency_ms: number }> }>("/api/settings")
export const updateSetting = (key: string, value: string) =>
  fetchAPI(`/api/settings/${key}`, { method: "PUT", body: JSON.stringify({ value }) })
