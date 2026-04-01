"use client"

import { useState } from "react"
import { DashboardShell } from "@/components/dashboard-shell"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
  SelectGroup,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"
import { formatDate } from "@/lib/utils"
import { useExperiments, useProposals } from "@/hooks/use-api"
import * as api from "@/lib/api"
import { mockExperiments, mockProposals } from "@/lib/mock-data"
import type { Experiment, ParameterSweepResult, ParameterChangeProposal } from "@/lib/types"
import {
  FlaskConical,
  Plus,
  ChevronDown,
  ChevronRight,
  Check,
  X,
  Download,
  Loader2,
  ArrowRight,
  ShieldAlert,
} from "lucide-react"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceDot,
} from "recharts"

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PARAMETER_CATEGORIES = [
  { label: "Model Hyperparameters", value: "model_hyperparam", params: ["xgboost.n_estimators", "xgboost.max_depth", "xgboost.learning_rate", "elastic_net.alpha", "elastic_net.l1_ratio", "arima.p", "arima.d", "arima.q"] },
  { label: "Ensemble Weights", value: "ensemble_weight", params: ["ensemble.xgboost_weight", "ensemble.elastic_net_weight", "ensemble.arima_weight", "ensemble.sentiment_weight"] },
  { label: "Screening Thresholds", value: "screening_threshold", params: ["screening.max_peg", "screening.min_fcf_yield", "screening.piotroski_threshold", "screening.composite_threshold"] },
  { label: "Risk Constants", value: "risk_constant", params: ["risk.max_position_pct", "risk.risk_per_trade_pct", "risk.min_cash_reserve_pct", "risk.correlation_threshold", "risk.high_model_disagreement_threshold"] },
  { label: "Sentiment Weights", value: "sentiment_weight", params: ["sentiment.finnhub_weight", "sentiment.newsapi_weight"] },
  { label: "Goal Parameters", value: "goal_param", params: ["goal.target_return_pct", "goal.max_loss_pct", "goal.deviation_trigger_pct", "goal.pace_tolerance"] },
]

const EXPERIMENT_TYPES = [
  "hyperparameter_sweep",
  "weight_tuning",
  "stress_test",
  "threshold_tuning",
  "feature_experiment",
  "model_comparison",
]

const DATA_SOURCES = ["mock", "emery", "dow_jones", "custom"]

const PHASES = ["pre_server", "paper_trading", "live"]

const SWEEP_METRICS = ["win_rate", "sharpe_ratio", "max_drawdown"]

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

// ---------------------------------------------------------------------------
// Tab bar (mirrors goals page pattern)
// ---------------------------------------------------------------------------

type Tab = "experiments" | "sweeps" | "compare" | "approvals"

function TabBar({ tab, setTab }: { tab: Tab; setTab: (t: Tab) => void }) {
  const tabs: { id: Tab; label: string }[] = [
    { id: "experiments", label: "Experiments" },
    { id: "sweeps", label: "Parameter Sweeps" },
    { id: "compare", label: "Model Comparison" },
    { id: "approvals", label: "Approvals & Export" },
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
// Status badge helper
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    completed: "bg-emerald-500/15 text-emerald-600 border-emerald-500/30",
    running: "bg-blue-500/15 text-blue-600 border-blue-500/30",
    pending: "",
    failed: "bg-red-500/15 text-red-600 border-red-500/30",
    cancelled: "bg-gray-500/15 text-gray-600 border-gray-500/30",
  }
  return (
    <Badge variant="outline" className={cn("text-xs font-medium", styles[status] || "")}>
      {status}
    </Badge>
  )
}

// ---------------------------------------------------------------------------
// Tab 1: Experiments
// ---------------------------------------------------------------------------

function ExperimentsTab() {
  const { data: apiExperiments, mutate } = useExperiments()
  const experiments = apiExperiments ?? mockExperiments

  const [showForm, setShowForm] = useState(false)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // Form state
  const [userName, setUserName] = useState("joe")
  const [expType, setExpType] = useState("")
  const [expName, setExpName] = useState("")
  const [expDesc, setExpDesc] = useState("")
  const [dataSource, setDataSource] = useState("mock")
  const [phase, setPhase] = useState("pre_server")

  const handleSubmit = async () => {
    if (!expType || !expName) return
    setSubmitting(true)
    try {
      await api.createExperiment({
        user_name: userName,
        experiment_type: expType,
        name: expName,
        description: expDesc || undefined,
        data_source: dataSource,
        phase,
      })
      await mutate()
      setShowForm(false)
      setExpName("")
      setExpDesc("")
      setExpType("")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Experiments</h2>
        <Button size="sm" onClick={() => setShowForm(!showForm)} className="gap-1">
          <Plus className="h-4 w-4" />
          New Experiment
        </Button>
      </div>

      {/* New experiment form */}
      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">New Experiment</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              <div className="space-y-2">
                <Label>User</Label>
                <Select value={userName} onValueChange={setUserName}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="joe">Joe</SelectItem>
                    <SelectItem value="jared">Jared</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Type</Label>
                <Select value={expType} onValueChange={setExpType}>
                  <SelectTrigger><SelectValue placeholder="Select type" /></SelectTrigger>
                  <SelectContent>
                    {EXPERIMENT_TYPES.map((t) => (
                      <SelectItem key={t} value={t}>{t.replace(/_/g, " ")}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Name</Label>
                <Input value={expName} onChange={(e) => setExpName(e.target.value)} placeholder="Experiment name" />
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Input value={expDesc} onChange={(e) => setExpDesc(e.target.value)} placeholder="Optional description" />
              </div>
              <div className="space-y-2">
                <Label>Data Source</Label>
                <Select value={dataSource} onValueChange={setDataSource}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {DATA_SOURCES.map((s) => (
                      <SelectItem key={s} value={s}>{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Phase</Label>
                <Select value={phase} onValueChange={setPhase}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {PHASES.map((p) => (
                      <SelectItem key={p} value={p}>{p.replace(/_/g, " ")}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="mt-4 flex gap-2">
              <Button onClick={handleSubmit} disabled={submitting || !expType || !expName} className="gap-1">
                {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                Create
              </Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Experiments table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-8" />
                <TableHead>Name</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Phase</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {experiments.map((exp) => (
                <ExperimentRow
                  key={exp.id}
                  experiment={exp}
                  expanded={expandedId === exp.id}
                  onToggle={() => setExpandedId(expandedId === exp.id ? null : exp.id)}
                />
              ))}
              {experiments.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-sm text-muted-foreground py-8">
                    No experiments yet. Create one to get started.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}

function ExperimentRow({
  experiment,
  expanded,
  onToggle,
}: {
  experiment: Experiment
  expanded: boolean
  onToggle: () => void
}) {
  return (
    <>
      <TableRow className="cursor-pointer hover:bg-muted/50" onClick={onToggle}>
        <TableCell className="w-8">
          {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </TableCell>
        <TableCell className="font-medium">{experiment.name}</TableCell>
        <TableCell className="text-sm">{experiment.user_name}</TableCell>
        <TableCell className="text-sm text-muted-foreground">{experiment.experiment_type.replace(/_/g, " ")}</TableCell>
        <TableCell><StatusBadge status={experiment.status} /></TableCell>
        <TableCell className="text-sm text-muted-foreground">{experiment.phase ?? "—"}</TableCell>
        <TableCell className="text-sm text-muted-foreground whitespace-nowrap">{formatDate(experiment.created_at)}</TableCell>
      </TableRow>
      {expanded && (
        <TableRow>
          <TableCell colSpan={7} className="bg-muted/30 p-4">
            <div className="grid gap-4 md:grid-cols-2">
              {Object.keys(experiment.parameters).length > 0 && (
                <div>
                  <span className="text-xs font-semibold uppercase text-muted-foreground">Parameters</span>
                  <pre className="mt-1 rounded border bg-background p-2 text-xs font-mono overflow-x-auto">
                    {JSON.stringify(experiment.parameters, null, 2)}
                  </pre>
                </div>
              )}
              {Object.keys(experiment.results).length > 0 && (
                <div>
                  <span className="text-xs font-semibold uppercase text-muted-foreground">Results</span>
                  <pre className="mt-1 rounded border bg-background p-2 text-xs font-mono overflow-x-auto">
                    {JSON.stringify(experiment.results, null, 2)}
                  </pre>
                </div>
              )}
            </div>
            {experiment.notes && (
              <div className="mt-3">
                <span className="text-xs font-semibold uppercase text-muted-foreground">Notes</span>
                <p className="mt-1 text-sm">{experiment.notes}</p>
              </div>
            )}
            {experiment.description && (
              <div className="mt-3">
                <span className="text-xs font-semibold uppercase text-muted-foreground">Description</span>
                <p className="mt-1 text-sm text-muted-foreground">{experiment.description}</p>
              </div>
            )}
          </TableCell>
        </TableRow>
      )}
    </>
  )
}

// ---------------------------------------------------------------------------
// Tab 2: Parameter Sweeps
// ---------------------------------------------------------------------------

function SweepsTab() {
  const [paramName, setParamName] = useState("")
  const [dataSource, setDataSource] = useState("mock")
  const [metric, setMetric] = useState("win_rate")
  const [sweepResult, setSweepResult] = useState<ParameterSweepResult | null>(null)
  const [loading, setLoading] = useState(false)

  const handleRunSweep = async () => {
    if (!paramName) return
    setLoading(true)
    try {
      const result = await api.runSweep({
        parameter_name: paramName,
        data_source: dataSource,
        optimize_metric: metric,
      })
      setSweepResult(result)
    } finally {
      setLoading(false)
    }
  }

  const bestPoint = sweepResult?.results_per_value.find(
    (p) => p.value === sweepResult.best_value
  )

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Parameter Sweep</CardTitle>
          <CardDescription>Select a parameter and metric, then run a sweep to find optimal values.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label>Parameter</Label>
              <Select value={paramName} onValueChange={setParamName}>
                <SelectTrigger><SelectValue placeholder="Select parameter" /></SelectTrigger>
                <SelectContent>
                  {PARAMETER_CATEGORIES.map((cat) => (
                    <SelectGroup key={cat.value}>
                      <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">{cat.label}</div>
                      {cat.params.map((p) => (
                        <SelectItem key={p} value={p}>{p}</SelectItem>
                      ))}
                    </SelectGroup>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Data Source</Label>
              <Select value={dataSource} onValueChange={setDataSource}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {DATA_SOURCES.map((s) => (
                    <SelectItem key={s} value={s}>{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Optimize Metric</Label>
              <Select value={metric} onValueChange={setMetric}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {SWEEP_METRICS.map((m) => (
                    <SelectItem key={m} value={m}>{m.replace(/_/g, " ")}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="mt-4">
            <Button onClick={handleRunSweep} disabled={loading || !paramName} className="gap-1">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FlaskConical className="h-4 w-4" />}
              Run Sweep
            </Button>
          </div>
        </CardContent>
      </Card>

      {sweepResult && (
        <>
          {/* Best value summary */}
          {bestPoint && sweepResult.best_value !== null && (
            <Card className="border-emerald-500/30">
              <CardContent className="pt-4">
                <div className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-emerald-500" />
                  <div>
                    <p className="text-sm font-semibold">
                      Best value: <span className="font-mono text-emerald-600">{sweepResult.best_value}</span>
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {sweepResult.best_metric_name}: <span className="font-mono">{sweepResult.best_metric_value?.toFixed(4)}</span>
                      {" | "}win_rate: <span className="font-mono">{bestPoint.win_rate.toFixed(4)}</span>
                      {" | "}max_drawdown: <span className="font-mono">{bestPoint.max_drawdown.toFixed(4)}</span>
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Chart */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Sweep: {sweepResult.parameter_name}
              </CardTitle>
              <CardDescription>
                {sweepResult.values_tested.length} values tested | optimizing {sweepResult.best_metric_name}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={sweepResult.results_per_value}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis
                      dataKey="value"
                      tick={{ fontSize: 11 }}
                      label={{ value: sweepResult.parameter_name, position: "insideBottom", offset: -5, fontSize: 11 }}
                    />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip
                      formatter={(value: number | undefined) => (value ?? 0).toFixed(4)}
                      labelFormatter={(label) => `${sweepResult.parameter_name}: ${label}`}
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="win_rate"
                      stroke="#10b981"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      name="Win Rate"
                    />
                    <Line
                      type="monotone"
                      dataKey="max_drawdown"
                      stroke="#ef4444"
                      strokeWidth={2}
                      strokeDasharray="5 5"
                      dot={{ r: 3 }}
                      name="Max Drawdown"
                    />
                    {sweepResult.best_value !== null && bestPoint && (
                      <ReferenceDot
                        x={sweepResult.best_value}
                        y={bestPoint[metric as keyof typeof bestPoint] as number}
                        r={6}
                        fill="#10b981"
                        stroke="#fff"
                        strokeWidth={2}
                      />
                    )}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Data table */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Sweep Data Points</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Value</TableHead>
                    <TableHead className="text-right">Win Rate</TableHead>
                    <TableHead className="text-right">Sharpe</TableHead>
                    <TableHead className="text-right">Max Drawdown</TableHead>
                    <TableHead className="text-right">Profit Factor</TableHead>
                    <TableHead className="text-right">Trades</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sweepResult.results_per_value.map((point) => {
                    const isBest = point.value === sweepResult.best_value
                    return (
                      <TableRow key={point.value} className={cn(isBest && "bg-emerald-500/10")}>
                        <TableCell className="font-mono font-medium">
                          {point.value}
                          {isBest && <Badge className="ml-2" variant="secondary">Best</Badge>}
                        </TableCell>
                        <TableCell className="text-right font-mono">{point.win_rate.toFixed(4)}</TableCell>
                        <TableCell className="text-right font-mono">{point.sharpe_ratio.toFixed(4)}</TableCell>
                        <TableCell className="text-right font-mono text-red-500">{point.max_drawdown.toFixed(4)}</TableCell>
                        <TableCell className="text-right font-mono">{point.profit_factor.toFixed(4)}</TableCell>
                        <TableCell className="text-right font-mono">{point.total_trades}</TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tab 3: Model Comparison
// ---------------------------------------------------------------------------

function CompareTab() {
  const { data: apiExperiments } = useExperiments()
  const experiments = apiExperiments ?? mockExperiments

  const completedExps = experiments.filter((e) => e.status === "completed")

  const [expA, setExpA] = useState("")
  const [expB, setExpB] = useState("")

  const experimentA = completedExps.find((e) => e.id === expA)
  const experimentB = completedExps.find((e) => e.id === expB)

  // Joe vs Jared: latest completed per user per type
  const userExps: Record<string, Record<string, Experiment>> = {}
  for (const exp of completedExps) {
    if (!userExps[exp.user_name]) userExps[exp.user_name] = {}
    const existing = userExps[exp.user_name][exp.experiment_type]
    if (!existing || new Date(exp.created_at) > new Date(existing.created_at)) {
      userExps[exp.user_name][exp.experiment_type] = exp
    }
  }

  const joeExps = userExps["joe"] ?? {}
  const jaredExps = userExps["jared"] ?? {}
  const sharedTypes = Array.from(new Set([...Object.keys(joeExps), ...Object.keys(jaredExps)]))

  const COMPARE_METRICS = ["win_rate", "sharpe_ratio", "max_drawdown"] as const

  return (
    <div className="space-y-4">
      {/* Side-by-side picker */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Compare Experiments</CardTitle>
          <CardDescription>Select two completed experiments to compare metrics side by side.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>Experiment A</Label>
              <Select value={expA} onValueChange={setExpA}>
                <SelectTrigger><SelectValue placeholder="Select experiment" /></SelectTrigger>
                <SelectContent>
                  {completedExps.map((e) => (
                    <SelectItem key={e.id} value={e.id}>{e.name} ({e.user_name})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Experiment B</Label>
              <Select value={expB} onValueChange={setExpB}>
                <SelectTrigger><SelectValue placeholder="Select experiment" /></SelectTrigger>
                <SelectContent>
                  {completedExps.map((e) => (
                    <SelectItem key={e.id} value={e.id}>{e.name} ({e.user_name})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Side-by-side cards */}
      {experimentA && experimentB && (
        <div className="grid gap-4 md:grid-cols-2">
          {[experimentA, experimentB].map((exp) => (
            <Card key={exp.id}>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">{exp.name}</CardTitle>
                <CardDescription>{exp.user_name} | {exp.experiment_type.replace(/_/g, " ")}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {COMPARE_METRICS.map((m) => {
                    const valA = (experimentA.results[m] as number) ?? null
                    const valB = (experimentB.results[m] as number) ?? null
                    const thisVal = (exp.results[m] as number) ?? null
                    const otherVal = exp === experimentA ? valB : valA
                    const isBetter =
                      thisVal !== null &&
                      otherVal !== null &&
                      (m === "max_drawdown" ? thisVal < otherVal : thisVal > otherVal)
                    return (
                      <div key={m} className="flex items-center justify-between rounded border p-2">
                        <span className="text-sm text-muted-foreground">{m.replace(/_/g, " ")}</span>
                        <span className={cn("font-mono text-sm font-semibold", isBetter && "text-emerald-600")}>
                          {thisVal !== null ? thisVal.toFixed(4) : "—"}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Joe vs Jared */}
      {sharedTypes.length > 0 && (
        <>
          <Separator />
          <h3 className="text-lg font-semibold">Joe vs Jared</h3>
          <p className="text-sm text-muted-foreground">Latest completed experiment per user per type.</p>
          <div className="space-y-4">
            {sharedTypes.map((type) => {
              const joeExp = joeExps[type]
              const jaredExp = jaredExps[type]
              return (
                <Card key={type}>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">{type.replace(/_/g, " ")}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-4 md:grid-cols-2">
                      {[{ label: "Joe", exp: joeExp }, { label: "Jared", exp: jaredExp }].map(({ label, exp }) => (
                        <div key={label} className="rounded-lg border p-3">
                          <p className="text-sm font-semibold">{label}</p>
                          {exp ? (
                            <div className="mt-2 space-y-1">
                              <p className="text-xs text-muted-foreground">{exp.name}</p>
                              {COMPARE_METRICS.map((m) => {
                                const thisVal = (exp.results[m] as number) ?? null
                                const otherExp = label === "Joe" ? jaredExp : joeExp
                                const otherVal = otherExp ? (otherExp.results[m] as number) ?? null : null
                                const isBetter =
                                  thisVal !== null &&
                                  otherVal !== null &&
                                  (m === "max_drawdown" ? thisVal < otherVal : thisVal > otherVal)
                                return (
                                  <div key={m} className="flex justify-between text-xs">
                                    <span className="text-muted-foreground">{m.replace(/_/g, " ")}</span>
                                    <span className={cn("font-mono", isBetter && "text-emerald-600")}>
                                      {thisVal !== null ? thisVal.toFixed(4) : "—"}
                                    </span>
                                  </div>
                                )
                              })}
                            </div>
                          ) : (
                            <p className="mt-2 text-xs text-muted-foreground">No completed experiment</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tab 4: Approvals & Export
// ---------------------------------------------------------------------------

function ApprovalsTab() {
  const { data: apiProposals, mutate } = useProposals()
  const proposals = apiProposals ?? mockProposals

  const [approveUser, setApproveUser] = useState("joe")
  const [processingId, setProcessingId] = useState<string | null>(null)

  const handleApprove = async (id: string) => {
    setProcessingId(id)
    try {
      await api.approveProposal(id, approveUser)
      await mutate()
    } finally {
      setProcessingId(null)
    }
  }

  const handleReject = async (id: string) => {
    setProcessingId(id)
    try {
      await api.rejectProposal(id)
      await mutate()
    } finally {
      setProcessingId(null)
    }
  }

  return (
    <div className="space-y-4">
      {/* Approver selector */}
      <div className="flex items-center gap-3">
        <Label className="text-sm">Approving as:</Label>
        <Select value={approveUser} onValueChange={setApproveUser}>
          <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="joe">Joe</SelectItem>
            <SelectItem value="jared">Jared</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Proposals table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Parameter Change Proposals</CardTitle>
          <CardDescription>Review and approve parameter changes from experiments.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Parameter</TableHead>
                <TableHead>Change</TableHead>
                <TableHead>Metric Change</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Approval</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {proposals.map((p) => (
                <ProposalRow
                  key={p.id}
                  proposal={p}
                  processingId={processingId}
                  onApprove={() => handleApprove(p.id)}
                  onReject={() => handleReject(p.id)}
                />
              ))}
              {proposals.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-sm text-muted-foreground py-8">
                    No proposals yet.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Export section */}
      <Separator />
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Export</CardTitle>
          <CardDescription>Download experiment data for offline analysis.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            <Button variant="outline" className="gap-2" asChild>
              <a href={`${API_URL}/api/training/export/experiments?format=csv`} download>
                <Download className="h-4 w-4" />
                Export CSV
              </a>
            </Button>
            <Button variant="outline" className="gap-2" asChild>
              <a href={`${API_URL}/api/training/export/experiments?format=xlsx`} download>
                <Download className="h-4 w-4" />
                Export XLSX
              </a>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function ProposalRow({
  proposal,
  processingId,
  onApprove,
  onReject,
}: {
  proposal: ParameterChangeProposal
  processingId: string | null
  onApprove: () => void
  onReject: () => void
}) {
  const isProcessing = processingId === proposal.id
  const isPending = proposal.status === "pending" || proposal.status === "joe_approved" || proposal.status === "jared_approved"

  // Metric change display
  const metricKeys = Array.from(new Set([...Object.keys(proposal.metric_before), ...Object.keys(proposal.metric_after)]))

  return (
    <TableRow>
      <TableCell>
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-medium">{proposal.parameter_name}</span>
          {proposal.requires_dual_approval && (
            <Badge variant="outline" className="bg-amber-500/15 text-amber-600 border-amber-500/30 text-xs">
              <ShieldAlert className="mr-1 h-3 w-3" />
              Dual approval
            </Badge>
          )}
        </div>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-1 text-sm">
          <span className="font-mono">{proposal.current_value}</span>
          <ArrowRight className="h-3 w-3 text-muted-foreground" />
          <span className="font-mono font-semibold">{proposal.proposed_value}</span>
        </div>
      </TableCell>
      <TableCell>
        <div className="space-y-0.5">
          {metricKeys.map((k) => {
            const before = proposal.metric_before[k]
            const after = proposal.metric_after[k]
            if (before === undefined || after === undefined) return null
            const improved = k === "max_drawdown" ? after < before : after > before
            return (
              <div key={k} className="flex items-center gap-1 text-xs">
                <span className="text-muted-foreground">{k}:</span>
                <span className={cn("font-mono", improved ? "text-emerald-600" : "text-red-500")}>
                  {before.toFixed(2)} → {after.toFixed(2)}
                </span>
              </div>
            )
          })}
        </div>
      </TableCell>
      <TableCell>
        <StatusBadge status={proposal.status} />
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <ApprovalSlot label="Joe" approved={proposal.joe_approved_at !== null} />
          <ApprovalSlot label="Jared" approved={proposal.jared_approved_at !== null} />
        </div>
      </TableCell>
      <TableCell className="text-right">
        {isPending && (
          <div className="flex justify-end gap-1">
            <Button size="sm" variant="outline" onClick={onApprove} disabled={isProcessing} className="gap-1 text-emerald-600 hover:text-emerald-700">
              {isProcessing ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
              Approve
            </Button>
            <Button size="sm" variant="outline" onClick={onReject} disabled={isProcessing} className="gap-1 text-red-500 hover:text-red-600">
              <X className="h-3 w-3" />
              Reject
            </Button>
          </div>
        )}
      </TableCell>
    </TableRow>
  )
}

function ApprovalSlot({ label, approved }: { label: string; approved: boolean }) {
  return (
    <div className={cn(
      "flex items-center gap-1 rounded border px-2 py-0.5 text-xs",
      approved ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-600" : "border-gray-200 text-muted-foreground"
    )}>
      {approved ? <Check className="h-3 w-3" /> : <span className="h-3 w-3" />}
      {label}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function TrainingLabPage() {
  const [tab, setTab] = useState<Tab>("experiments")

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div>
          <div className="flex items-center gap-2">
            <FlaskConical className="h-7 w-7 text-primary" />
            <h1 className="text-2xl font-bold">Training Lab</h1>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Run experiments, sweep parameters, compare models, and approve changes.
          </p>
        </div>

        <TabBar tab={tab} setTab={setTab} />

        {tab === "experiments" && <ExperimentsTab />}
        {tab === "sweeps" && <SweepsTab />}
        {tab === "compare" && <CompareTab />}
        {tab === "approvals" && <ApprovalsTab />}
      </div>
    </DashboardShell>
  )
}
