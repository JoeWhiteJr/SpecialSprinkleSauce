"use client"

import useSWR from "swr"
import * as api from "@/lib/api"

const defaultOptions = {
  revalidateOnFocus: false,
  dedupingInterval: 30000,
}

export function useHealth() {
  return useSWR("health", api.getHealth, { ...defaultOptions, refreshInterval: 30000 })
}

export function usePositions(status?: string) {
  return useSWR(["positions", status], () => api.getPositions(status), defaultOptions)
}

export function usePnL() {
  return useSWR("pnl", api.getPnL, defaultOptions)
}

export function usePortfolioSummary() {
  return useSWR("portfolio-summary", api.getPortfolioSummary, defaultOptions)
}

export function useRecommendations(status?: string) {
  return useSWR(["recommendations", status], () => api.getRecommendations(status), defaultOptions)
}

export function useJournal(params?: { ticker?: string; action?: string; page?: number }) {
  return useSWR(["journal", params], () => api.getJournal(params), defaultOptions)
}

export function useJournalEntry(id: string) {
  return useSWR(id ? ["journal", id] : null, () => api.getJournalEntry(id), defaultOptions)
}

export function useDebates() {
  return useSWR("debates", api.getDebates, defaultOptions)
}

export function useDebate(pipelineRunId: string) {
  return useSWR(
    pipelineRunId ? ["debate", pipelineRunId] : null,
    () => api.getDebate(pipelineRunId),
    defaultOptions
  )
}

export function useJuryVotes(pipelineRunId: string) {
  return useSWR(
    pipelineRunId ? ["jury", pipelineRunId] : null,
    () => api.getJuryVotes(pipelineRunId),
    defaultOptions
  )
}

export function useJuryStats() {
  return useSWR("jury-stats", api.getJuryStats, defaultOptions)
}

export function useOverrides(status?: string) {
  return useSWR(["overrides", status], () => api.getOverrides(status), defaultOptions)
}

export function useAlerts(params?: { severity?: string; acknowledged?: boolean }) {
  return useSWR(["alerts", params], () => api.getAlerts(params), defaultOptions)
}

export function useStreak() {
  return useSWR("streak", api.getStreak, defaultOptions)
}

export function useBiasMetrics() {
  return useSWR("bias-metrics", api.getBiasMetrics, defaultOptions)
}

export function useBiasHistory() {
  return useSWR("bias-history", api.getBiasHistory, defaultOptions)
}

export function useLatestScreening() {
  return useSWR("screening-latest", api.getLatestScreening, defaultOptions)
}

export function useScreeningHistory() {
  return useSWR("screening-history", api.getScreeningHistory, defaultOptions)
}

export function useSettings() {
  return useSWR("settings", api.getSettings, defaultOptions)
}

export function useNotifications() {
  return useSWR("notifications", api.getNotifications, defaultOptions)
}

export function useNotificationChannels() {
  return useSWR("notification-channels", api.getNotificationChannels, defaultOptions)
}

export function useNotificationPreferences() {
  return useSWR("notification-preferences", api.getNotificationPreferences, defaultOptions)
}

export function useBacktestRuns() {
  return useSWR("backtest-runs", api.getBacktestRuns, defaultOptions)
}

export function useBacktestRun(runId: string) {
  return useSWR(runId ? ["backtest-run", runId] : null, () => api.getBacktestRun(runId), defaultOptions)
}

export function useBacktestStrategies() {
  return useSWR("backtest-strategies", api.getBacktestStrategies, defaultOptions)
}

export function useDrift() {
  return useSWR("drift", api.getDrift, defaultOptions)
}

export function useTargets() {
  return useSWR("targets", api.getTargets, defaultOptions)
}

export function usePaperTradingSummary() {
  return useSWR("paper-trading-summary", api.getPaperTradingSummary, defaultOptions)
}

export function useEmergencyStatus() {
  return useSWR("emergency-status", api.getEmergencyStatus, { ...defaultOptions, refreshInterval: 5000 })
}

export function useShutdownHistory() {
  return useSWR("shutdown-history", api.getShutdownHistory, defaultOptions)
}
