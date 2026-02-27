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
import { Skeleton } from "@/components/ui/skeleton"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import {
  FileText,
  Download,
  Calendar,
  DollarSign,
  TrendingUp,
  BarChart3,
  Activity,
} from "lucide-react"
import { usePaperTradingSummary } from "@/hooks/use-api"
import { mockPaperTradingSummary } from "@/lib/mock-data"
import { formatCurrency, formatPercent, cn } from "@/lib/utils"
import type { PaperTradingSummary } from "@/lib/types"

function SummarySkeleton() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-72" />
        </CardHeader>
        <CardContent className="space-y-2">
          <Skeleton className="h-5 w-56" />
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-5 w-40" />
        </CardContent>
      </Card>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardHeader className="pb-2">
              <Skeleton className="h-4 w-24" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-32" />
            </CardContent>
          </Card>
        ))}
      </div>
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-36" />
        </CardHeader>
        <CardContent className="space-y-2">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-5 w-44" />
        </CardContent>
      </Card>
    </div>
  )
}

function handleExport(data: unknown, prefix: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `report-${prefix}-${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
}

export default function ReportsPage() {
  const { data: apiSummary, isLoading: summaryLoading } = usePaperTradingSummary()

  const summary: PaperTradingSummary = apiSummary ?? mockPaperTradingSummary

  const [tab, setTab] = useState("daily")
  const [dailyDate, setDailyDate] = useState("")
  const [weekDate, setWeekDate] = useState("")
  const [monthValue, setMonthValue] = useState("")

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <FileText className="h-8 w-8" />
            Reports
          </h1>
          <p className="text-muted-foreground mt-1">
            Generate and export trading performance reports.
          </p>
        </div>

        <Tabs value={tab} onValueChange={setTab}>
          <TabsList>
            <TabsTrigger value="daily">Daily</TabsTrigger>
            <TabsTrigger value="weekly">Weekly</TabsTrigger>
            <TabsTrigger value="monthly">Monthly</TabsTrigger>
            <TabsTrigger value="paper">Paper Trading Summary</TabsTrigger>
          </TabsList>

          {/* Daily Tab */}
          <TabsContent value="daily" className="mt-4 space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="h-5 w-5" />
                  Daily Report
                </CardTitle>
                <CardDescription>
                  Generate a report for a specific trading day.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-end gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="daily-date">Date</Label>
                    <Input
                      id="daily-date"
                      type="date"
                      value={dailyDate}
                      onChange={(e) => setDailyDate(e.target.value)}
                      className="w-48"
                    />
                  </div>
                  <Button
                    onClick={() => console.log("Generate daily report for:", dailyDate)}
                    disabled={!dailyDate}
                  >
                    Generate
                  </Button>
                </div>
                <Separator />
                <div className="text-center py-8 text-muted-foreground">
                  Select a date and click Generate to view the daily report.
                </div>
              </CardContent>
            </Card>
            <div className="flex justify-end">
              <Button
                variant="outline"
                onClick={() => handleExport({ type: "daily", date: dailyDate }, "daily")}
              >
                <Download className="h-4 w-4 mr-2" />
                Export JSON
              </Button>
            </div>
          </TabsContent>

          {/* Weekly Tab */}
          <TabsContent value="weekly" className="mt-4 space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="h-5 w-5" />
                  Weekly Report
                </CardTitle>
                <CardDescription>
                  Generate a report for a trading week.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-end gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="week-date">Week Start Date</Label>
                    <Input
                      id="week-date"
                      type="date"
                      value={weekDate}
                      onChange={(e) => setWeekDate(e.target.value)}
                      className="w-48"
                    />
                  </div>
                  <Button
                    onClick={() => console.log("Generate weekly report for:", weekDate)}
                    disabled={!weekDate}
                  >
                    Generate
                  </Button>
                </div>
                <Separator />
                <div className="text-center py-8 text-muted-foreground">
                  Select a week start date and click Generate to view the weekly report.
                </div>
              </CardContent>
            </Card>
            <div className="flex justify-end">
              <Button
                variant="outline"
                onClick={() => handleExport({ type: "weekly", week_start: weekDate }, "weekly")}
              >
                <Download className="h-4 w-4 mr-2" />
                Export JSON
              </Button>
            </div>
          </TabsContent>

          {/* Monthly Tab */}
          <TabsContent value="monthly" className="mt-4 space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="h-5 w-5" />
                  Monthly Report
                </CardTitle>
                <CardDescription>
                  Generate a report for a trading month.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-end gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="month-value">Month</Label>
                    <Input
                      id="month-value"
                      type="month"
                      value={monthValue}
                      onChange={(e) => setMonthValue(e.target.value)}
                      className="w-48"
                    />
                  </div>
                  <Button
                    onClick={() => console.log("Generate monthly report for:", monthValue)}
                    disabled={!monthValue}
                  >
                    Generate
                  </Button>
                </div>
                <Separator />
                <div className="text-center py-8 text-muted-foreground">
                  Select a month and click Generate to view the monthly report.
                </div>
              </CardContent>
            </Card>
            <div className="flex justify-end">
              <Button
                variant="outline"
                onClick={() => handleExport({ type: "monthly", month: monthValue }, "monthly")}
              >
                <Download className="h-4 w-4 mr-2" />
                Export JSON
              </Button>
            </div>
          </TabsContent>

          {/* Paper Trading Summary Tab */}
          <TabsContent value="paper" className="mt-4 space-y-4">
            {summaryLoading ? (
              <SummarySkeleton />
            ) : (
              <>
                {/* Setup Info */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <FileText className="h-5 w-5" />
                      Paper Trading Setup
                    </CardTitle>
                    <CardDescription>
                      Configuration for the current paper trading session.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-4 md:grid-cols-3">
                      <div>
                        <p className="text-sm text-muted-foreground">Start Date</p>
                        <p className="text-lg font-semibold">{summary.setup.start_date}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Initial Capital</p>
                        <p className="text-lg font-semibold">
                          {formatCurrency(summary.setup.initial_capital)}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Trading Mode</p>
                        <Badge className="bg-blue-600 hover:bg-blue-700 text-sm px-3 py-1">
                          {summary.setup.trading_mode.toUpperCase()}
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Stat Cards */}
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground">
                        Total Value
                      </CardTitle>
                      <DollarSign className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">
                        {formatCurrency(summary.current.total_value)}
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground">
                        Total P&L
                      </CardTitle>
                      <TrendingUp
                        className={cn(
                          "h-4 w-4",
                          summary.current.total_pnl >= 0
                            ? "text-emerald-500"
                            : "text-red-500"
                        )}
                      />
                    </CardHeader>
                    <CardContent>
                      <div
                        className={cn(
                          "text-2xl font-bold",
                          summary.current.total_pnl >= 0
                            ? "text-emerald-500"
                            : "text-red-500"
                        )}
                      >
                        {formatCurrency(summary.current.total_pnl)}
                      </div>
                      <p
                        className={cn(
                          "text-xs",
                          summary.current.total_return >= 0
                            ? "text-emerald-500"
                            : "text-red-500"
                        )}
                      >
                        {formatPercent(summary.current.total_return)}
                      </p>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground">
                        Sharpe Ratio
                      </CardTitle>
                      <BarChart3 className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">
                        {summary.current.sharpe_ratio.toFixed(2)}
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground">
                        Max Drawdown
                      </CardTitle>
                      <Activity className="h-4 w-4 text-red-500" />
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold text-red-500">
                        {formatPercent(summary.current.max_drawdown)}
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Additional Stats */}
                <Card>
                  <CardHeader>
                    <CardTitle>Additional Statistics</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-4 md:grid-cols-3">
                      <div>
                        <p className="text-sm text-muted-foreground">Total Trades</p>
                        <p className="text-2xl font-bold">{summary.current.total_trades}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Win Rate</p>
                        <p className="text-2xl font-bold">{summary.current.win_rate}%</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Days Active</p>
                        <p className="text-2xl font-bold">{summary.current.days_active}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </>
            )}
            <div className="flex justify-end">
              <Button
                variant="outline"
                onClick={() => handleExport(summary, "paper-trading-summary")}
              >
                <Download className="h-4 w-4 mr-2" />
                Export JSON
              </Button>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </DashboardShell>
  )
}
