"use client"

import { useState } from "react"
import { DashboardShell } from "@/components/dashboard-shell"
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
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
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { TestTube2, TrendingUp, TrendingDown, BarChart3, Target } from "lucide-react"
import { useBacktestRuns, useBacktestStrategies } from "@/hooks/use-api"
import { mockBacktestRuns, mockBacktestStrategies } from "@/lib/mock-data"
import { formatPercent, formatDate, formatCurrency } from "@/lib/utils"
import type { BacktestRun, BacktestStrategy } from "@/lib/types"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts"

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-72" />
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-32" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default function BacktestingPage() {
  const { data: apiRuns, isLoading: runsLoading } = useBacktestRuns()
  const { data: apiStrategies, isLoading: strategiesLoading } = useBacktestStrategies()

  const runs = apiRuns ?? mockBacktestRuns
  const strategies = apiStrategies ?? mockBacktestStrategies

  const isLoading = runsLoading || strategiesLoading

  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const [ticker, setTicker] = useState("")
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")
  const [strategyId, setStrategyId] = useState("")

  const selectedRun = runs.find((r) => r.id === selectedRunId) ?? null

  const handleRunBacktest = () => {
    console.log("Run backtest:", { ticker, startDate, endDate, strategyId })
  }

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <TestTube2 className="h-8 w-8" />
            Backtesting
          </h1>
          <p className="text-muted-foreground mt-1">
            Run historical backtests against trading strategies.
          </p>
        </div>

        {isLoading ? (
          <LoadingSkeleton />
        ) : (
          <>
            {/* Run Form */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">New Backtest</CardTitle>
                <CardDescription>
                  Configure and launch a historical backtest run
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
                  <div className="space-y-2">
                    <Label htmlFor="ticker">Ticker</Label>
                    <Input
                      id="ticker"
                      placeholder="e.g. NVDA"
                      value={ticker}
                      onChange={(e) => setTicker(e.target.value.toUpperCase())}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="start-date">Start Date</Label>
                    <Input
                      id="start-date"
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="end-date">End Date</Label>
                    <Input
                      id="end-date"
                      type="date"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="strategy">Strategy</Label>
                    <Select value={strategyId} onValueChange={setStrategyId}>
                      <SelectTrigger id="strategy">
                        <SelectValue placeholder="Select strategy" />
                      </SelectTrigger>
                      <SelectContent>
                        {strategies.map((s) => (
                          <SelectItem key={s.id} value={s.id}>
                            {s.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex items-end">
                    <Button onClick={handleRunBacktest} className="w-full">
                      Run Backtest
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Results Table */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Backtest Results</CardTitle>
                <CardDescription>Click a row to view detailed results</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Ticker</TableHead>
                      <TableHead>Strategy</TableHead>
                      <TableHead className="text-right">Return%</TableHead>
                      <TableHead className="text-right">Sharpe</TableHead>
                      <TableHead className="text-right">Max Drawdown</TableHead>
                      <TableHead className="text-right">Win Rate%</TableHead>
                      <TableHead className="text-right">Trades</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {runs.map((run) => {
                      const strategyLabel =
                        strategies.find((s) => s.id === run.strategy)?.name ?? run.strategy
                      return (
                        <TableRow
                          key={run.id}
                          className="cursor-pointer hover:bg-muted/50"
                          onClick={() => setSelectedRunId(run.id)}
                        >
                          <TableCell className="whitespace-nowrap text-sm">
                            {formatDate(run.created_at)}
                          </TableCell>
                          <TableCell className="font-medium">{run.ticker}</TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {strategyLabel}
                          </TableCell>
                          <TableCell className="text-right">
                            <span
                              className={
                                run.metrics.total_return >= 0
                                  ? "text-emerald-500"
                                  : "text-red-500"
                              }
                            >
                              {formatPercent(run.metrics.total_return)}
                            </span>
                          </TableCell>
                          <TableCell className="text-right font-mono text-sm">
                            {run.metrics.sharpe_ratio.toFixed(2)}
                          </TableCell>
                          <TableCell className="text-right">
                            <span className="text-red-500">
                              {formatPercent(run.metrics.max_drawdown)}
                            </span>
                          </TableCell>
                          <TableCell className="text-right text-sm">
                            {run.metrics.win_rate.toFixed(1)}%
                          </TableCell>
                          <TableCell className="text-right text-sm">
                            {run.metrics.total_trades}
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            {/* Selected Run Detail */}
            {selectedRun && (
              <>
                <Separator />

                {/* Metric Stat Cards */}
                <div className="grid gap-4 md:grid-cols-4">
                  <Card>
                    <CardHeader className="pb-2">
                      <CardDescription className="flex items-center gap-1">
                        <TrendingUp className="h-3 w-3" />
                        Total Return
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <span
                        className={`text-2xl font-bold ${
                          selectedRun.metrics.total_return >= 0
                            ? "text-emerald-500"
                            : "text-red-500"
                        }`}
                      >
                        {formatPercent(selectedRun.metrics.total_return)}
                      </span>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardDescription className="flex items-center gap-1">
                        <BarChart3 className="h-3 w-3" />
                        Sharpe Ratio
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <span className="text-2xl font-bold">
                        {selectedRun.metrics.sharpe_ratio.toFixed(2)}
                      </span>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardDescription className="flex items-center gap-1">
                        <TrendingDown className="h-3 w-3" />
                        Max Drawdown
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <span className="text-2xl font-bold text-red-500">
                        {formatPercent(selectedRun.metrics.max_drawdown)}
                      </span>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardDescription className="flex items-center gap-1">
                        <Target className="h-3 w-3" />
                        Win Rate
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <span className="text-2xl font-bold">
                        {selectedRun.metrics.win_rate.toFixed(1)}%
                      </span>
                    </CardContent>
                  </Card>
                </div>

                {/* Equity Curve Chart */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">
                      Equity Curve — {selectedRun.ticker}
                    </CardTitle>
                    <CardDescription>
                      {selectedRun.start_date} to {selectedRun.end_date}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[300px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={selectedRun.equity_curve}>
                          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                          <XAxis
                            dataKey="date"
                            tick={{ fontSize: 11 }}
                            tickFormatter={(v) => v.slice(5)}
                          />
                          <YAxis
                            tick={{ fontSize: 11 }}
                            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                          />
                          <Tooltip
                            formatter={(value: number | undefined) => [formatCurrency(value ?? 0), "Value"]}
                            labelFormatter={(label) => `Date: ${label}`}
                          />
                          <Line
                            type="monotone"
                            dataKey="value"
                            stroke="#3b82f6"
                            strokeWidth={2}
                            dot={false}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>

                {/* Trades Table */}
                {selectedRun.trades.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Trades</CardTitle>
                      <CardDescription>
                        {selectedRun.trades.length} trades executed during backtest
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="p-0">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Date</TableHead>
                            <TableHead>Action</TableHead>
                            <TableHead className="text-right">Price</TableHead>
                            <TableHead className="text-right">Shares</TableHead>
                            <TableHead className="text-right">P&L</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {selectedRun.trades.map((trade, i) => (
                            <TableRow key={i}>
                              <TableCell className="whitespace-nowrap text-sm">
                                {formatDate(trade.date)}
                              </TableCell>
                              <TableCell>
                                <Badge
                                  className={
                                    trade.action === "BUY"
                                      ? "bg-emerald-600 hover:bg-emerald-700"
                                      : "bg-red-600 hover:bg-red-700"
                                  }
                                >
                                  {trade.action}
                                </Badge>
                              </TableCell>
                              <TableCell className="text-right font-mono text-sm">
                                {formatCurrency(trade.price)}
                              </TableCell>
                              <TableCell className="text-right text-sm">
                                {trade.shares}
                              </TableCell>
                              <TableCell className="text-right">
                                {trade.pnl !== 0 ? (
                                  <span
                                    className={
                                      trade.pnl >= 0
                                        ? "text-emerald-500 font-medium"
                                        : "text-red-500 font-medium"
                                    }
                                  >
                                    {formatCurrency(trade.pnl)}
                                  </span>
                                ) : (
                                  <span className="text-muted-foreground">--</span>
                                )}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </CardContent>
                  </Card>
                )}
              </>
            )}
          </>
        )}
      </div>
    </DashboardShell>
  )
}
