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

// Notifications
export const getNotifications = () =>
  fetchAPI<import("./types").Notification[]>("/api/notifications")
export const getNotificationChannels = () =>
  fetchAPI<import("./types").NotificationChannel[]>("/api/notifications/channels")
export const sendTestNotification = (channel: string, message: string) =>
  fetchAPI("/api/notifications/test", { method: "POST", body: JSON.stringify({ channel, message }) })
export const getNotificationPreferences = () =>
  fetchAPI<import("./types").NotificationPreferences>("/api/notifications/preferences")

// Backtesting
export const runBacktest = (data: { ticker: string; start_date: string; end_date: string; strategy: string }) =>
  fetchAPI<import("./types").BacktestRun>("/api/backtesting/run", { method: "POST", body: JSON.stringify(data) })
export const getBacktestRuns = () =>
  fetchAPI<import("./types").BacktestRun[]>("/api/backtesting/runs")
export const getBacktestRun = (runId: string) =>
  fetchAPI<import("./types").BacktestRun>(`/api/backtesting/runs/${runId}`)
export const getBacktestStrategies = () =>
  fetchAPI<import("./types").BacktestStrategy[]>("/api/backtesting/strategies")

// Rebalancing
export const getDrift = () =>
  fetchAPI<import("./types").DriftAnalysis>("/api/rebalancing/drift")
export const getTargets = () =>
  fetchAPI<import("./types").TargetWeights>("/api/rebalancing/targets")
export const updateTargets = (weights: Record<string, number>) =>
  fetchAPI("/api/rebalancing/targets", { method: "PUT", body: JSON.stringify({ weights }) })
export const previewRebalance = () =>
  fetchAPI<import("./types").RebalancePreview>("/api/rebalancing/preview", { method: "POST" })
export const executeRebalance = () =>
  fetchAPI("/api/rebalancing/execute", { method: "POST" })

// Reports
export const getDailyReport = (date: string) =>
  fetchAPI<import("./types").DailyReport>(`/api/reports/daily/${date}`)
export const getWeeklyReport = (weekStart: string) =>
  fetchAPI<import("./types").WeeklyReport>(`/api/reports/weekly/${weekStart}`)
export const getMonthlyReport = (month: string) =>
  fetchAPI<import("./types").MonthlyReport>(`/api/reports/monthly/${month}`)
export const getPaperTradingSummary = () =>
  fetchAPI<import("./types").PaperTradingSummary>("/api/reports/paper-trading-summary")
export const exportReport = (reportType: string, period: string) =>
  fetchAPI(`/api/reports/export/${reportType}/${period}`)

// Emergency
export const emergencyShutdown = (data: { initiated_by: string; reason: string }) =>
  fetchAPI("/api/emergency/shutdown", { method: "POST", body: JSON.stringify(data) })
export const resumeTrading = (data: { approved_by: string }) =>
  fetchAPI("/api/emergency/resume", { method: "POST", body: JSON.stringify(data) })
export const getEmergencyStatus = () =>
  fetchAPI<import("./types").EmergencyStatus>("/api/emergency/status")
export const getShutdownHistory = () =>
  fetchAPI<import("./types").ShutdownEvent[]>("/api/emergency/history")
export const cancelAllOrders = () =>
  fetchAPI("/api/emergency/cancel-all-orders", { method: "POST" })
export const forcePaperMode = () =>
  fetchAPI("/api/emergency/force-paper-mode", { method: "POST" })
