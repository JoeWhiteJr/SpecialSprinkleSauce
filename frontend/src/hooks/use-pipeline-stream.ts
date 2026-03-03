"use client"

import { useCallback, useReducer, useRef } from "react"
import type { PipelineNodeState, PipelineStreamEvent } from "@/lib/types"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

const INITIAL_NODES: PipelineNodeState[] = [
  { name: "quant_scoring", label: "Quant Scoring", index: 0, status: "pending", data: null, skipReason: null, durationMs: null },
  { name: "wasden_watch", label: "Wasden Watch", index: 1, status: "pending", data: null, skipReason: null, durationMs: null },
  { name: "bull_researcher", label: "Bull Researcher", index: 2, status: "pending", data: null, skipReason: null, durationMs: null },
  { name: "bear_researcher", label: "Bear Researcher", index: 3, status: "pending", data: null, skipReason: null, durationMs: null },
  { name: "debate", label: "Debate", index: 4, status: "pending", data: null, skipReason: null, durationMs: null },
  { name: "jury_spawn", label: "Jury Spawn", index: 5, status: "pending", data: null, skipReason: null, durationMs: null },
  { name: "jury_aggregate", label: "Jury Aggregate", index: 6, status: "pending", data: null, skipReason: null, durationMs: null },
  { name: "risk_check", label: "Risk Check", index: 7, status: "pending", data: null, skipReason: null, durationMs: null },
  { name: "pre_trade_validation", label: "Pre-Trade Validation", index: 8, status: "pending", data: null, skipReason: null, durationMs: null },
  { name: "decision", label: "Decision", index: 9, status: "pending", data: null, skipReason: null, durationMs: null },
]

type StreamStatus = "idle" | "connecting" | "streaming" | "completed" | "error"

interface StreamState {
  status: StreamStatus
  nodes: PipelineNodeState[]
  pipelineRunId: string | null
  result: Record<string, unknown> | null
  error: string | null
}

type StreamAction =
  | { type: "RESET" }
  | { type: "CONNECTING" }
  | { type: "PIPELINE_START"; pipelineRunId: string }
  | { type: "NODE_START"; nodeIndex: number }
  | { type: "NODE_COMPLETE"; nodeIndex: number; data: Record<string, unknown>; durationMs: number }
  | { type: "NODE_SKIPPED"; nodeIndex: number; reason: string }
  | { type: "PIPELINE_COMPLETE"; result: Record<string, unknown> }
  | { type: "PIPELINE_ERROR"; error: string }

function reducer(state: StreamState, action: StreamAction): StreamState {
  switch (action.type) {
    case "RESET":
      return { status: "idle", nodes: INITIAL_NODES.map((n) => ({ ...n })), pipelineRunId: null, result: null, error: null }
    case "CONNECTING":
      return { ...state, status: "connecting", nodes: INITIAL_NODES.map((n) => ({ ...n })), result: null, error: null }
    case "PIPELINE_START":
      return { ...state, status: "streaming", pipelineRunId: action.pipelineRunId }
    case "NODE_START": {
      const nodes = state.nodes.map((n) => (n.index === action.nodeIndex ? { ...n, status: "running" as const } : n))
      return { ...state, nodes }
    }
    case "NODE_COMPLETE": {
      const nodes = state.nodes.map((n) =>
        n.index === action.nodeIndex ? { ...n, status: "completed" as const, data: action.data, durationMs: action.durationMs } : n
      )
      return { ...state, nodes }
    }
    case "NODE_SKIPPED": {
      const nodes = state.nodes.map((n) =>
        n.index === action.nodeIndex ? { ...n, status: "skipped" as const, skipReason: action.reason } : n
      )
      return { ...state, nodes }
    }
    case "PIPELINE_COMPLETE":
      return { ...state, status: "completed", result: action.result }
    case "PIPELINE_ERROR":
      return { ...state, status: "error", error: action.error }
    default:
      return state
  }
}

export function usePipelineStream() {
  const [state, dispatch] = useReducer(reducer, {
    status: "idle",
    nodes: INITIAL_NODES.map((n) => ({ ...n })),
    pipelineRunId: null,
    result: null,
    error: null,
  })

  const abortRef = useRef<AbortController | null>(null)

  const startPipeline = useCallback(async (ticker: string, price?: number) => {
    // Abort any existing stream
    if (abortRef.current) {
      abortRef.current.abort()
    }

    const controller = new AbortController()
    abortRef.current = controller

    dispatch({ type: "CONNECTING" })

    try {
      const res = await fetch(`${API_URL}/api/pipeline/run-stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker, price: price || 0.0 }),
        signal: controller.signal,
      })

      if (!res.ok) {
        dispatch({ type: "PIPELINE_ERROR", error: `HTTP ${res.status}: ${res.statusText}` })
        return
      }

      const reader = res.body?.getReader()
      if (!reader) {
        dispatch({ type: "PIPELINE_ERROR", error: "No response body" })
        return
      }

      const decoder = new TextDecoder()
      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // Parse SSE events from buffer
        const lines = buffer.split("\n")
        buffer = lines.pop() || "" // Keep incomplete line in buffer

        let eventData: string | null = null
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            eventData = line.slice(6)
          } else if (line === "" && eventData !== null) {
            // End of event
            try {
              const event: PipelineStreamEvent = JSON.parse(eventData)
              handleEvent(event, dispatch)
            } catch {
              // Skip malformed events
            }
            eventData = null
          }
        }
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return
      dispatch({ type: "PIPELINE_ERROR", error: String(err) })
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
    startPipeline,
    reset,
    isRunning: state.status === "connecting" || state.status === "streaming",
  }
}

function handleEvent(event: PipelineStreamEvent, dispatch: React.Dispatch<StreamAction>) {
  switch (event.type) {
    case "pipeline_start":
      dispatch({ type: "PIPELINE_START", pipelineRunId: event.pipeline_run_id || "" })
      break
    case "node_start":
      if (event.node_index !== undefined) {
        dispatch({ type: "NODE_START", nodeIndex: event.node_index })
      }
      break
    case "node_complete":
      if (event.node_index !== undefined) {
        dispatch({
          type: "NODE_COMPLETE",
          nodeIndex: event.node_index,
          data: event.data || {},
          durationMs: event.duration_ms || 0,
        })
      }
      break
    case "node_skipped":
      if (event.node_index !== undefined) {
        dispatch({ type: "NODE_SKIPPED", nodeIndex: event.node_index, reason: event.reason || "" })
      }
      break
    case "pipeline_complete":
      dispatch({ type: "PIPELINE_COMPLETE", result: event.result || {} })
      break
    case "pipeline_error":
      dispatch({ type: "PIPELINE_ERROR", error: event.error || "Unknown error" })
      break
  }
}
