"use client"

import { useState } from "react"
import { DashboardShell } from "@/components/dashboard-shell"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"
import { getGoalRuns, runTargetSweep } from "@/lib/api"
import { useGoalStream } from "@/hooks/use-goal-stream"
import type { GoalConfig, GoalTrade, GoalRunResult } from "@/hooks/use-goal-stream"
import {
  Target,
  Play,
  RotateCcw,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
  DollarSign,
  Calendar,
  ShieldAlert,
} from "lucide-react"

// ---------------------------------------------------------------------------
// Tab selector
// ---------------------------------------------------------------------------

type Tab = "new" | "active" | "sweep"

function TabBar({ tab, setTab }: { tab: Tab; setTab: (t: Tab) => void }) {
  const tabs: { id: Tab; label: string }[] = [
    { id: "new", label: "New Goal" },
    { id: "active", label: "Active Goals" },
    { id: "sweep", label: "Target Sweep" },
  ]

  return (
    <div className="flex gap-1 rounded-lg border bg-muted p-1">
      {tabs.map((t) => (
        <button
          key={t.id}
          onClick={() => setTab(t.id)}
          className={cn(
            "rounded-md px-4 py-1.5 text-sm font-medium transition-colors",
            tab === t.id ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
          )}
        >
          {t.label}
        </button>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// New Goal tab
// ---------------------------------------------------------------------------

function NewGoalTab() {
  const [capital, setCapital] = useState("1000")
  const [targetPct, setTargetPct] = useState("2")
  const [timeframeDays, setTimeframeDays] = useState("5")
  const [maxLossPct, setMaxLossPct] = useState("1")

  const { status, result, error, startGoal, reset, isRunning } = useGoalStream()

  const handleRun = () => {
    const config: GoalConfig = {
      capital: parseFloat(capital) || 1000,
      target_return_pct: (parseFloat(targetPct) || 2) / 100,
      timeframe_days: parseInt(timeframeDays) || 5,
      max_loss_pct: (parseFloat(maxLossPct) || 1) / 100,
    }
    startGoal(config)
  }

  const goalCapital = parseFloat(capital) || 0
  const goalTarget = (parseFloat(targetPct) || 0) / 100
  const goalDollar = goalCapital * goalTarget
  const goalMaxLoss = goalCapital * ((parseFloat(maxLossPct) || 0) / 100)

  return (
    <div className="space-y-6">
      {/* Goal configuration form */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="h-5 w-5" />
            Define Your Goal
          </CardTitle>
          <CardDescription>
            Set a financial target and let the AI agents figure out the best trades to hit it.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div className="space-y-2">
              <Label htmlFor="capital">Capital ($)</Label>
              <Input id="capital" type="number" value={capital} onChange={(e) => setCapital(e.target.value)} min="1" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="target">Target Return (%)</Label>
              <Input id="target" type="number" value={targetPct} onChange={(e) => setTargetPct(e.target.value)} min="0.1" step="0.1" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="timeframe">Timeframe (days)</Label>
              <Input id="timeframe" type="number" value={timeframeDays} onChange={(e) => setTimeframeDays(e.target.value)} min="1" max="90" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="maxloss">Max Loss (%)</Label>
              <Input id="maxloss" type="number" value={maxLossPct} onChange={(e) => setMaxLossPct(e.target.value)} min="0.1" step="0.1" />
            </div>
          </div>

          {/* Live preview */}
          <div className="mt-4 rounded-lg border bg-muted/50 p-3 text-sm">
            <span className="font-medium">Goal: </span>
            Turn <span className="font-semibold text-emerald-600">${goalCapital.toLocaleString()}</span> into{" "}
            <span className="font-semibold text-emerald-600">${(goalCapital + goalDollar).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>{" "}
            in <span className="font-semibold">{timeframeDays}</span> trading days,
            risking at most <span className="font-semibold text-red-600">${goalMaxLoss.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
          </div>

          <div className="mt-4 flex gap-2">
            <Button onClick={handleRun} disabled={isRunning} className="gap-2">
              {isRunning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {isRunning ? "Running..." : "Run Goal"}
            </Button>
            {status !== "idle" && (
              <Button variant="outline" onClick={reset} className="gap-2">
                <RotateCcw className="h-4 w-4" /> Reset
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Error display */}
      {error && (
        <Card className="border-red-300 bg-red-50">
          <CardContent className="flex items-center gap-2 pt-4">
            <AlertTriangle className="h-5 w-5 text-red-500" />
            <span className="text-sm text-red-700">{error}</span>
          </CardContent>
        </Card>
      )}

      {/* Result display */}
      {result && <GoalResultCard result={result} />}
    </div>
  )
}

function GoalResultCard({ result }: { result: GoalRunResult }) {
  const statusColors: Record<string, string> = {
    active: "bg-emerald-500/15 text-emerald-600 border-emerald-500/30",
    planning: "bg-blue-500/15 text-blue-600 border-blue-500/30",
    achieved: "bg-emerald-500/15 text-emerald-600 border-emerald-500/30",
    failed: "bg-red-500/15 text-red-600 border-red-500/30",
    stopped: "bg-gray-500/15 text-gray-600 border-gray-500/30",
  }

  return (
    <div className="space-y-4">
      {/* Summary */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-emerald-500" />
              Goal Result
            </CardTitle>
            <Badge variant="outline" className={cn("text-sm font-semibold", statusColors[result.status] || "")}>
              {result.status.toUpperCase()}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatCard icon={DollarSign} label="Capital" value={`$${result.config.capital.toLocaleString()}`} />
            <StatCard icon={TrendingUp} label="Target" value={`+${(result.config.target_return_pct * 100).toFixed(1)}%`} />
            <StatCard icon={Calendar} label="Timeframe" value={`${result.config.timeframe_days} days`} />
            <StatCard icon={ShieldAlert} label="Max Loss" value={`-${(result.config.max_loss_pct * 100).toFixed(1)}%`} />
          </div>
        </CardContent>
      </Card>

      {/* Candidates */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Candidates ({result.candidates.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {result.candidates.map((ticker) => (
              <Badge key={ticker} variant="outline">{ticker}</Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Portfolio allocations */}
      {result.portfolio_allocations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Portfolio Allocation</CardTitle>
            <CardDescription>Debate outcome: {result.portfolio_debate_outcome}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {result.portfolio_allocations.map((alloc) => (
                <div key={alloc.ticker} className="flex items-center justify-between rounded-md border p-2">
                  <span className="font-medium">{alloc.ticker}</span>
                  <span className="text-sm text-muted-foreground">{alloc.rationale}</span>
                  <Badge variant="secondary">{alloc.allocation_pct}%</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Trade plan */}
      {result.trade_plan.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Trade Plan ({result.trade_plan.length} trades)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="p-2">Ticker</th>
                    <th className="p-2">Action</th>
                    <th className="p-2">Shares</th>
                    <th className="p-2">Entry Est.</th>
                    <th className="p-2">Stop Loss</th>
                    <th className="p-2">Target Exit</th>
                    <th className="p-2">Position $</th>
                    <th className="p-2">Day</th>
                  </tr>
                </thead>
                <tbody>
                  {result.trade_plan.map((trade, i) => (
                    <tr key={i} className="border-b">
                      <td className="p-2 font-medium">{trade.ticker}</td>
                      <td className="p-2">
                        <Badge variant="outline" className={trade.action === "BUY" ? "text-emerald-600" : "text-red-600"}>
                          {trade.action}
                        </Badge>
                      </td>
                      <td className="p-2">{trade.shares}</td>
                      <td className="p-2">${trade.entry_price_est.toFixed(2)}</td>
                      <td className="p-2 text-red-600">${trade.stop_loss_price.toFixed(2)}</td>
                      <td className="p-2 text-emerald-600">${trade.target_exit_price.toFixed(2)}</td>
                      <td className="p-2">${trade.position_dollar.toFixed(2)}</td>
                      <td className="p-2">{trade.day_target}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function StatCard({ icon: Icon, label, value }: { icon: typeof DollarSign; label: string; value: string }) {
  return (
    <div className="rounded-lg border p-3">
      <div className="flex items-center gap-2 text-muted-foreground">
        <Icon className="h-4 w-4" />
        <span className="text-xs">{label}</span>
      </div>
      <div className="mt-1 text-lg font-semibold">{value}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Active Goals tab (placeholder — reads from API)
// ---------------------------------------------------------------------------

function ActiveGoalsTab() {
  const [goals, setGoals] = useState<GoalRunResult[]>([])
  const [loading, setLoading] = useState(false)

  const loadGoals = async () => {
    setLoading(true)
    try {
      const data = await getGoalRuns()
      setGoals(data)
    } catch {
      // Silently handle fetch errors
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Active Goals</CardTitle>
          <Button variant="outline" size="sm" onClick={loadGoals} disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Load Goals"}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {goals.length === 0 ? (
          <p className="text-sm text-muted-foreground">No active goals. Create one in the &quot;New Goal&quot; tab.</p>
        ) : (
          <div className="space-y-3">
            {goals.map((goal) => (
              <div key={goal.goal_id} className="rounded-lg border p-4">
                <div className="flex items-center justify-between">
                  <span className="font-medium">
                    ${goal.config.capital.toLocaleString()} @ +{(goal.config.target_return_pct * 100).toFixed(1)}%
                  </span>
                  <Badge variant="outline">{goal.status}</Badge>
                </div>
                <div className="mt-2 text-sm text-muted-foreground">
                  {goal.trade_plan.length} trades planned | {goal.config.timeframe_days} days
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Target Sweep tab
// ---------------------------------------------------------------------------

interface SweepResult {
  sweep_id: string
  ticker: string
  frontier: Array<{ target_pct: number; success_rate: number; avg_return: number; avg_drawdown: number }>
  sweet_spot: { target_pct: number; success_rate: number; avg_return: number; avg_drawdown: number } | null
}

function TargetSweepTab() {
  const [ticker, setTicker] = useState("NVDA")
  const [loading, setLoading] = useState(false)
  const [sweepResult, setSweepResult] = useState<SweepResult | null>(null)

  const runSweep = async () => {
    setLoading(true)
    try {
      const data = await runTargetSweep({ ticker, capital: 1000, timeframe_days: 5, max_loss_pct: 0.01 })
      setSweepResult(data as SweepResult)
    } catch {
      // Silently handle fetch errors
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Target Sweep</CardTitle>
          <CardDescription>
            Test multiple target levels against historical data to find the sweet spot.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <div className="space-y-2">
              <Label htmlFor="sweep-ticker">Ticker</Label>
              <Input id="sweep-ticker" value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} className="w-32" />
            </div>
            <div className="flex items-end">
              <Button onClick={runSweep} disabled={loading} className="gap-2">
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                Run Sweep
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {sweepResult && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Risk/Accuracy Frontier — {sweepResult.ticker}
            </CardTitle>
            {sweepResult.sweet_spot && (
              <CardDescription>
                Sweet spot: {(sweepResult.sweet_spot.target_pct * 100).toFixed(1)}% target
                @ {(sweepResult.sweet_spot.success_rate * 100).toFixed(0)}% success rate
              </CardDescription>
            )}
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="p-2">Target %</th>
                    <th className="p-2">Success Rate</th>
                    <th className="p-2">Avg Return</th>
                    <th className="p-2">Avg Drawdown</th>
                  </tr>
                </thead>
                <tbody>
                  {sweepResult.frontier.map((point) => {
                    const isSweetSpot = sweepResult.sweet_spot && point.target_pct === sweepResult.sweet_spot.target_pct
                    return (
                      <tr key={point.target_pct} className={cn("border-b", isSweetSpot && "bg-emerald-50 font-semibold")}>
                        <td className="p-2">
                          {(point.target_pct * 100).toFixed(1)}%
                          {isSweetSpot && <Badge className="ml-2" variant="secondary">Sweet Spot</Badge>}
                        </td>
                        <td className="p-2">{(point.success_rate * 100).toFixed(1)}%</td>
                        <td className="p-2 text-emerald-600">+{(point.avg_return * 100).toFixed(2)}%</td>
                        <td className="p-2 text-red-600">-{(point.avg_drawdown * 100).toFixed(2)}%</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function GoalsPage() {
  const [tab, setTab] = useState<Tab>("new")

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div>
          <div className="flex items-center gap-2">
            <Target className="h-7 w-7 text-primary" />
            <h1 className="text-2xl font-bold">Goals</h1>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">Task-based trading with defined financial targets</p>
        </div>

        <TabBar tab={tab} setTab={setTab} />

        {tab === "new" && <NewGoalTab />}
        {tab === "active" && <ActiveGoalsTab />}
        {tab === "sweep" && <TargetSweepTab />}
      </div>
    </DashboardShell>
  )
}
