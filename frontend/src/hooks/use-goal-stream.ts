"use client"

import { useCallback, useReducer, useRef } from "react"
import { API_URL, getHeaders } from "@/lib/api"

export interface GoalConfig {
  capital: number
  target_return_pct: number
  timeframe_days: number
  max_loss_pct: number
}

export interface GoalTrade {
  ticker: string
  action: string
  shares: number
  entry_price_est: number
  position_dollar: number
  stop_loss_price: number
  target_exit_price: number
  contribution_target_pct: number
  day_target: number
  status: string
}

export interface GoalRunResult {
  goal_id: string
  config: {
    capital: number
    target_return_pct: number
    timeframe_days: number
    max_loss_pct: number
    target_dollar: number
    max_loss_dollar: number
  }
  status: string
  candidates: string[]
  portfolio_debate_outcome: string
  portfolio_allocations: Array<{ ticker: string; allocation_pct: number; rationale: string }>
  trade_plan: GoalTrade[]
  cumulative_pnl: number
  cumulative_pnl_pct: number
  remaining_capital: number
  remaining_target_pct: number
  errors: Array<{ stage: string; error: string }>
}

type StreamStatus = "idle" | "connecting" | "streaming" | "completed" | "error"

interface GoalStreamState {
  status: StreamStatus
  result: GoalRunResult | null
  error: string | null
}

type GoalStreamAction =
  | { type: "RESET" }
  | { type: "CONNECTING" }
  | { type: "GOAL_COMPLETE"; result: GoalRunResult }
  | { type: "GOAL_ERROR"; error: string }

function reducer(state: GoalStreamState, action: GoalStreamAction): GoalStreamState {
  switch (action.type) {
    case "RESET":
      return { status: "idle", result: null, error: null }
    case "CONNECTING":
      return { status: "connecting", result: null, error: null }
    case "GOAL_COMPLETE":
      return { status: "completed", result: action.result, error: null }
    case "GOAL_ERROR":
      return { status: "error", result: null, error: action.error }
    default:
      return state
  }
}

export function useGoalStream() {
  const [state, dispatch] = useReducer(reducer, {
    status: "idle",
    result: null,
    error: null,
  })

  const abortRef = useRef<AbortController | null>(null)

  const startGoal = useCallback(async (config: GoalConfig) => {
    if (abortRef.current) {
      abortRef.current.abort()
    }

    const controller = new AbortController()
    abortRef.current = controller

    dispatch({ type: "CONNECTING" })

    try {
      const res = await fetch(`${API_URL}/api/goals/run-stream`, {
        method: "POST",
        headers: getHeaders(),
        body: JSON.stringify(config),
        signal: controller.signal,
      })

      if (!res.ok) {
        dispatch({ type: "GOAL_ERROR", error: `HTTP ${res.status}: ${res.statusText}` })
        return
      }

      const reader = res.body?.getReader()
      if (!reader) {
        dispatch({ type: "GOAL_ERROR", error: "No response body" })
        return
      }

      const decoder = new TextDecoder()
      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split("\n")
        buffer = lines.pop() || ""

        let eventData: string | null = null
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            eventData = line.slice(6)
          } else if (line === "" && eventData !== null) {
            try {
              const result: GoalRunResult = JSON.parse(eventData)
              dispatch({ type: "GOAL_COMPLETE", result })
            } catch {
              // Skip malformed events
            }
            eventData = null
          }
        }
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return
      dispatch({ type: "GOAL_ERROR", error: String(err) })
    }
  }, [])

  const reset = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort()
      abortRef.current = null
    }
    dispatch({ type: "RESET" })
  }, [])

  return {
    ...state,
    startGoal,
    reset,
    isRunning: state.status === "connecting" || state.status === "streaming",
  }
}
