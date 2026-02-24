"use client"

import { useState } from "react"
import { DashboardShell } from "@/components/dashboard-shell"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table"
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert"
import {
  AlertTriangle,
  TrendingDown,
  CheckCircle,
  PlayCircle,
  Flame,
  Info,
  ShieldAlert,
} from "lucide-react"
import { useAlerts, useStreak } from "@/hooks/use-api"
import { mockAlerts, mockStreak } from "@/lib/mock-data"
import { formatDate, formatDateTime, formatCurrency } from "@/lib/utils"
import type { RiskAlert } from "@/lib/types"

function severityBadge(severity: RiskAlert["severity"]) {
  switch (severity) {
    case "info":
      return <Badge variant="outline" className="border-blue-500 text-blue-500">Info</Badge>
    case "warning":
      return <Badge className="bg-amber-600 hover:bg-amber-700">Warning</Badge>
    case "critical":
      return <Badge variant="destructive">Critical</Badge>
  }
}

function streakStatusBadge(status: string) {
  switch (status) {
    case "active":
      return <Badge className="bg-emerald-600 hover:bg-emerald-700">Active</Badge>
    case "warning":
      return <Badge className="bg-amber-600 hover:bg-amber-700">Warning</Badge>
    case "halted":
      return <Badge variant="destructive">Halted</Badge>
    default:
      return <Badge variant="outline">{status}</Badge>
  }
}

function streakColor(streak: number): string {
  if (streak === 0) return "text-emerald-500"
  if (streak <= 2) return "text-amber-500"
  return "text-red-500"
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-10 w-16" />
            </CardHeader>
          </Card>
        ))}
      </div>
      <Card>
        <CardContent className="py-6 space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

export default function AlertsPage() {
  const { data: apiAlerts, isLoading: alertsLoading } = useAlerts()
  const { data: apiStreak, isLoading: streakLoading } = useStreak()

  const alerts = apiAlerts ?? mockAlerts
  const streak = apiStreak ?? mockStreak

  const [severityFilter, setSeverityFilter] = useState<string>("all")
  const [acknowledgedAlerts, setAcknowledgedAlerts] = useState<Set<string>>(new Set())

  const isLoading = alertsLoading || streakLoading

  const filteredAlerts = alerts.filter((alert) => {
    if (severityFilter === "all") return true
    return alert.severity === severityFilter
  })

  const handleAcknowledge = (alertId: string) => {
    setAcknowledgedAlerts((prev) => {
      const next = new Set(prev)
      next.add(alertId)
      return next
    })
    // In production, this would call acknowledgeAlert API
  }

  const isAcknowledged = (alert: RiskAlert) =>
    alert.acknowledged || acknowledgedAlerts.has(alert.id)

  const showResumeTrading = streak.status === "warning" || streak.status === "halted"

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <AlertTriangle className="h-8 w-8" />
            Consecutive Loss Warning
          </h1>
          <p className="text-muted-foreground mt-1">
            Monitor loss streaks and risk alerts. Trading halts automatically at 5 consecutive losses.
          </p>
        </div>

        {showResumeTrading && (
          <Alert variant="destructive">
            <ShieldAlert className="h-4 w-4" />
            <AlertTitle>Trading {streak.status === "halted" ? "Halted" : "Warning"}</AlertTitle>
            <AlertDescription className="flex items-center justify-between">
              <span>
                {streak.status === "halted"
                  ? "Trading has been automatically halted due to consecutive losses. Manual review required."
                  : "Approaching consecutive loss threshold. Review positions before continuing."}
              </span>
              <Button size="sm" variant="outline" className="ml-4 shrink-0">
                <PlayCircle className="mr-1 h-4 w-4" />
                Resume Trading
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {isLoading ? (
          <LoadingSkeleton />
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardHeader className="pb-2">
                  <CardDescription className="flex items-center gap-1">
                    <Flame className="h-3 w-3" />
                    Current Streak
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-3">
                    <span className={`text-5xl font-bold ${streakColor(streak.current_streak)}`}>
                      {streak.current_streak}
                    </span>
                    {streakStatusBadge(streak.status)}
                  </div>
                  {streak.last_loss_ticker && (
                    <p className="text-sm text-muted-foreground mt-2">
                      Last loss: {streak.last_loss_ticker}
                      {streak.last_loss_date && ` on ${formatDate(streak.last_loss_date)}`}
                    </p>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardDescription className="flex items-center gap-1">
                    <TrendingDown className="h-3 w-3" />
                    Net P&L
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <span
                    className={`text-3xl font-bold ${
                      streak.net_pnl >= 0 ? "text-emerald-500" : "text-red-500"
                    }`}
                  >
                    {formatCurrency(streak.net_pnl)}
                  </span>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardDescription className="flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3" />
                    Max Streak
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <span className={`text-3xl font-bold ${streakColor(streak.max_streak)}`}>
                    {streak.max_streak}
                  </span>
                  <p className="text-sm text-muted-foreground mt-1">All-time worst</p>
                </CardContent>
              </Card>
            </div>

            <Separator />

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold">Alert History</h2>
                <Select value={severityFilter} onValueChange={setSeverityFilter}>
                  <SelectTrigger className="w-[160px]">
                    <SelectValue placeholder="Filter severity" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Severities</SelectItem>
                    <SelectItem value="info">Info</SelectItem>
                    <SelectItem value="warning">Warning</SelectItem>
                    <SelectItem value="critical">Critical</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Card>
                <CardContent className="p-0">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Date</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Severity</TableHead>
                        <TableHead className="max-w-[400px]">Message</TableHead>
                        <TableHead>Ticker</TableHead>
                        <TableHead>Acknowledged</TableHead>
                        <TableHead className="text-right">Action</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredAlerts.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                            No alerts match the current filter
                          </TableCell>
                        </TableRow>
                      ) : (
                        filteredAlerts.map((alert) => (
                          <TableRow key={alert.id}>
                            <TableCell className="whitespace-nowrap text-sm">
                              {formatDateTime(alert.created_at)}
                            </TableCell>
                            <TableCell className="whitespace-nowrap">
                              <span className="text-sm font-mono">
                                {alert.alert_type.replace(/_/g, " ")}
                              </span>
                            </TableCell>
                            <TableCell>{severityBadge(alert.severity)}</TableCell>
                            <TableCell className="max-w-[400px] text-sm">
                              {alert.message}
                            </TableCell>
                            <TableCell>
                              {alert.ticker ? (
                                <Badge variant="outline">{alert.ticker}</Badge>
                              ) : (
                                <span className="text-muted-foreground">--</span>
                              )}
                            </TableCell>
                            <TableCell>
                              {isAcknowledged(alert) ? (
                                <div className="flex items-center gap-1 text-emerald-500">
                                  <CheckCircle className="h-4 w-4" />
                                  <span className="text-xs">
                                    {alert.acknowledged_by || "You"}
                                  </span>
                                </div>
                              ) : (
                                <span className="text-muted-foreground text-sm">No</span>
                              )}
                            </TableCell>
                            <TableCell className="text-right">
                              {!isAcknowledged(alert) && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleAcknowledge(alert.id)}
                                >
                                  Acknowledge
                                </Button>
                              )}
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </div>
          </>
        )}
      </div>
    </DashboardShell>
  )
}
