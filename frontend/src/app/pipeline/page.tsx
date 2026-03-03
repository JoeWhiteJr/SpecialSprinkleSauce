"use client"

import { useState } from "react"
import { DashboardShell } from "@/components/dashboard-shell"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { usePipelineStream } from "@/hooks/use-pipeline-stream"
import { cn } from "@/lib/utils"
import type { PipelineNodeState } from "@/lib/types"
import {
  Workflow,
  CheckCircle2,
  SkipForward,
  Circle,
  Loader2,
  Play,
  RotateCcw,
  ChevronDown,
  ChevronRight,
  ShieldAlert,
  TrendingUp,
  AlertTriangle,
} from "lucide-react"

function ActionBadge({ action }: { action: string }) {
  const variants: Record<string, string> = {
    BUY: "bg-emerald-500/15 text-emerald-600 border-emerald-500/30",
    SELL: "bg-red-500/15 text-red-600 border-red-500/30",
    HOLD: "bg-blue-500/15 text-blue-600 border-blue-500/30",
    BLOCKED: "bg-orange-500/15 text-orange-600 border-orange-500/30",
    ESCALATED: "bg-purple-500/15 text-purple-600 border-purple-500/30",
  }
  return (
    <Badge variant="outline" className={cn("text-sm font-semibold", variants[action] || "")}>
      {action}
    </Badge>
  )
}

function NodeIcon({ status }: { status: PipelineNodeState["status"] }) {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="h-5 w-5 text-emerald-500" />
    case "running":
      return <Circle className="h-5 w-5 text-blue-500 animate-pulse" />
    case "skipped":
      return <SkipForward className="h-5 w-5 text-amber-500" />
    default:
      return <Circle className="h-5 w-5 text-muted-foreground/40" />
  }
}

function NodeDataPreview({ node }: { node: PipelineNodeState }) {
  if (!node.data) return null
  const data = node.data

  switch (node.name) {
    case "quant_scoring":
      return (
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          <span className="text-muted-foreground">Composite:</span>
          <span className="font-mono">{Number(data.quant_composite).toFixed(3)}</span>
          <span className="text-muted-foreground">Std Dev:</span>
          <span className="font-mono">{Number(data.quant_std_dev).toFixed(3)}</span>
          <span className="text-muted-foreground">High Disagreement:</span>
          <span>{data.high_disagreement_flag ? "Yes" : "No"}</span>
        </div>
      )
    case "wasden_watch":
      return (
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          <span className="text-muted-foreground">Verdict:</span>
          <span className="font-semibold">{String(data.wasden_verdict)}</span>
          <span className="text-muted-foreground">Confidence:</span>
          <span className="font-mono">{(Number(data.wasden_confidence) * 100).toFixed(0)}%</span>
          <span className="text-muted-foreground">Vetoed:</span>
          <span>{data.wasden_vetoed ? "Yes" : "No"}</span>
        </div>
      )
    case "debate":
      return (
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          <span className="text-muted-foreground">Outcome:</span>
          <span className="font-semibold">{String(data.debate_outcome)}</span>
          <span className="text-muted-foreground">Rounds:</span>
          <span>{String(data.debate_rounds)}</span>
          <span className="text-muted-foreground">Agreed:</span>
          <span>{data.debate_agreed ? "Yes" : "No"}</span>
        </div>
      )
    case "jury_aggregate":
      return (
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          <span className="text-muted-foreground">Escalated:</span>
          <span>{data.jury_escalated ? "Yes" : "No"}</span>
          {typeof data.jury_result === "object" && data.jury_result !== null ? (
            <>
              <span className="text-muted-foreground">Decision:</span>
              <span className="font-semibold">{String((data.jury_result as Record<string, unknown>).decision)}</span>
            </>
          ) : null}
        </div>
      )
    case "risk_check":
      return (
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          <span className="text-muted-foreground">Passed:</span>
          <span className={data.risk_passed ? "text-emerald-500" : "text-red-500"}>{data.risk_passed ? "Yes" : "No"}</span>
          {Array.isArray(data.checks_failed) && data.checks_failed.length > 0 && (
            <>
              <span className="text-muted-foreground">Failed:</span>
              <span className="text-red-500">{(data.checks_failed as string[]).join(", ")}</span>
            </>
          )}
        </div>
      )
    case "pre_trade_validation":
      return (
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          <span className="text-muted-foreground">Passed:</span>
          <span className={data.pre_trade_passed ? "text-emerald-500" : "text-red-500"}>{data.pre_trade_passed ? "Yes" : "No"}</span>
        </div>
      )
    case "decision":
      return (
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          <span className="text-muted-foreground">Action:</span>
          <span className="font-semibold">{String(data.final_action)}</span>
          <span className="text-muted-foreground">Position Size:</span>
          <span className="font-mono">{(Number(data.recommended_position_size) * 100).toFixed(1)}%</span>
        </div>
      )
    default:
      return (
        <pre className="text-xs text-muted-foreground overflow-hidden whitespace-pre-wrap">
          {JSON.stringify(data, null, 2).slice(0, 200)}
        </pre>
      )
  }
}

function NodeStepper({ nodes }: { nodes: PipelineNodeState[] }) {
  const [expandedNodes, setExpandedNodes] = useState<Set<number>>(new Set())

  function toggleNode(index: number) {
    setExpandedNodes((prev) => {
      const next = new Set(prev)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }

  return (
    <div className="relative space-y-0">
      {nodes.map((node, i) => {
        const isExpanded = expandedNodes.has(i)
        const hasData = node.status === "completed" && node.data
        const isLast = i === nodes.length - 1

        return (
          <div key={node.name} className="relative flex gap-4">
            {/* Vertical connector line */}
            {!isLast && (
              <div
                className={cn(
                  "absolute left-[9px] top-6 w-0.5 bottom-0",
                  node.status === "skipped" ? "border-l-2 border-dashed border-amber-500/40" : "bg-border"
                )}
              />
            )}

            {/* Node icon */}
            <div className="relative z-10 flex-shrink-0 mt-0.5">
              <NodeIcon status={node.status} />
            </div>

            {/* Node content */}
            <div className={cn("flex-1 pb-6", isLast && "pb-0")}>
              <div
                className={cn(
                  "flex items-center gap-2 cursor-pointer select-none",
                  hasData && "hover:text-foreground"
                )}
                onClick={() => hasData && toggleNode(i)}
              >
                <span
                  className={cn(
                    "text-sm font-medium",
                    node.status === "pending" && "text-muted-foreground",
                    node.status === "running" && "text-blue-500",
                    node.status === "completed" && "text-foreground",
                    node.status === "skipped" && "text-amber-500"
                  )}
                >
                  {node.label}
                </span>
                {node.durationMs !== null && (
                  <span className="text-xs text-muted-foreground">({node.durationMs}ms)</span>
                )}
                {node.status === "skipped" && (
                  <Badge variant="outline" className="text-[10px] h-4 bg-amber-500/10 text-amber-600 border-amber-500/30">
                    skipped
                  </Badge>
                )}
                {hasData && (
                  isExpanded ? <ChevronDown className="h-3 w-3 text-muted-foreground" /> : <ChevronRight className="h-3 w-3 text-muted-foreground" />
                )}
              </div>

              {node.status === "skipped" && node.skipReason && (
                <p className="text-xs text-muted-foreground mt-1">{node.skipReason}</p>
              )}

              {hasData && isExpanded && (
                <div className="mt-2 p-3 rounded-md border bg-muted/50">
                  <NodeDataPreview node={node} />
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function PipelineResultSummary({ result }: { result: Record<string, unknown> }) {
  const decision = result.final_decision as Record<string, unknown> | undefined
  if (!decision) return null

  const action = String(decision.action || "")
  const reason = String(decision.reason || "")
  const positionSize = Number(decision.recommended_position_size || 0)
  const humanRequired = Boolean(decision.human_approval_required)

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Pipeline Result</CardTitle>
          <ActionBadge action={action} />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <span className="text-muted-foreground">Ticker:</span>
          <span className="font-semibold">{String(result.ticker || "")}</span>
          <span className="text-muted-foreground">Position Size:</span>
          <span className="font-mono">{(positionSize * 100).toFixed(1)}%</span>
        </div>
        <Separator />
        <p className="text-sm text-muted-foreground">{reason}</p>
        {humanRequired && (
          <div className="flex items-center gap-2 text-sm text-amber-600">
            <AlertTriangle className="h-4 w-4" />
            Human approval required
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default function PipelinePage() {
  const [ticker, setTicker] = useState("")
  const [price, setPrice] = useState("")
  const { status, nodes, pipelineRunId, result, error, isRunning, startPipeline, reset } = usePipelineStream()

  function handleRun() {
    if (!ticker.trim()) return
    startPipeline(ticker.trim().toUpperCase(), price ? parseFloat(price) : undefined)
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !isRunning && ticker.trim()) {
      handleRun()
    }
  }

  return (
    <DashboardShell>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <div className="flex items-center gap-2">
            <Workflow className="h-7 w-7 text-primary" />
            <h1 className="text-3xl font-bold tracking-tight">Pipeline Runner</h1>
          </div>
          <p className="text-muted-foreground mt-1">
            Run the 10-node decision pipeline and watch each step execute in real-time
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1fr_400px]">
          {/* Left column: Input + Node stepper */}
          <div className="space-y-6">
            {/* Input Card */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">Run Configuration</CardTitle>
                <CardDescription>Enter a ticker to run through the full decision pipeline</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-end gap-4">
                  <div className="space-y-2 flex-1">
                    <Label htmlFor="ticker">Ticker</Label>
                    <Input
                      id="ticker"
                      placeholder="e.g. NVDA, XOM, TSM"
                      value={ticker}
                      onChange={(e) => setTicker(e.target.value)}
                      onKeyDown={handleKeyDown}
                      disabled={isRunning}
                    />
                  </div>
                  <div className="space-y-2 w-32">
                    <Label htmlFor="price">Price (optional)</Label>
                    <Input
                      id="price"
                      type="number"
                      placeholder="0.00"
                      value={price}
                      onChange={(e) => setPrice(e.target.value)}
                      onKeyDown={handleKeyDown}
                      disabled={isRunning}
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={handleRun} disabled={isRunning || !ticker.trim()}>
                      {isRunning ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Running...
                        </>
                      ) : (
                        <>
                          <Play className="mr-2 h-4 w-4" />
                          Run Pipeline
                        </>
                      )}
                    </Button>
                    {status !== "idle" && (
                      <Button variant="outline" onClick={reset} disabled={isRunning}>
                        <RotateCcw className="mr-2 h-4 w-4" />
                        Reset
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Node Stepper */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">Pipeline Nodes</CardTitle>
                <CardDescription>
                  {status === "idle"
                    ? "10 nodes will execute sequentially"
                    : status === "connecting"
                    ? "Connecting to pipeline..."
                    : status === "streaming"
                    ? "Pipeline executing..."
                    : status === "completed"
                    ? "Pipeline complete"
                    : "Pipeline error"}
                  {pipelineRunId && (
                    <span className="ml-2 font-mono text-xs">{pipelineRunId.slice(0, 8)}</span>
                  )}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {status === "idle" ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Workflow className="h-12 w-12 mx-auto mb-3 opacity-30" />
                    <p className="text-sm">Enter a ticker and click Run Pipeline to start</p>
                  </div>
                ) : status === "connecting" ? (
                  <div className="space-y-4 py-4">
                    {Array.from({ length: 10 }).map((_, i) => (
                      <div key={i} className="flex items-center gap-4">
                        <Skeleton className="h-5 w-5 rounded-full" />
                        <Skeleton className="h-4 w-32" />
                      </div>
                    ))}
                  </div>
                ) : (
                  <ScrollArea className="max-h-[600px]">
                    <NodeStepper nodes={nodes} />
                  </ScrollArea>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Right column: Result summary */}
          <div className="space-y-6">
            {status === "completed" && result && (
              <PipelineResultSummary result={result} />
            )}

            {status === "error" && error && (
              <Card className="border-red-500/30">
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2">
                    <ShieldAlert className="h-5 w-5 text-red-500" />
                    <CardTitle className="text-lg text-red-500">Pipeline Error</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-red-400">{error}</p>
                </CardContent>
              </Card>
            )}

            {status === "streaming" && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg">Live Status</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-blue-500" />
                      <span>
                        {nodes.filter((n) => n.status === "completed").length} of {nodes.length} nodes complete
                      </span>
                    </div>
                    <div className="w-full bg-muted rounded-full h-2">
                      <div
                        className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${(nodes.filter((n) => n.status === "completed" || n.status === "skipped").length / nodes.length) * 100}%` }}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Quick test tickers */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">Quick Test</CardTitle>
                <CardDescription>Click to auto-fill test tickers</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { ticker: "NVDA", desc: "Agreement path" },
                    { ticker: "XOM", desc: "VETO path" },
                    { ticker: "TSM", desc: "Jury 5-5 tie" },
                    { ticker: "AAPL", desc: "Risk fail" },
                    { ticker: "NFLX", desc: "Jury majority" },
                    { ticker: "MSFT", desc: "Agreement path" },
                  ].map(({ ticker: t, desc }) => (
                    <Button
                      key={t}
                      variant="outline"
                      size="sm"
                      className="justify-start"
                      disabled={isRunning}
                      onClick={() => {
                        setTicker(t)
                        setPrice("")
                      }}
                    >
                      <span className="font-mono font-semibold mr-2">{t}</span>
                      <span className="text-xs text-muted-foreground">{desc}</span>
                    </Button>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </DashboardShell>
  )
}
