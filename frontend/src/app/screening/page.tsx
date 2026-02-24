"use client"

import { DashboardShell } from "@/components/dashboard-shell"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table"
import { Skeleton } from "@/components/ui/skeleton"
import { Filter, Clock, Calendar, ArrowDown, CheckCircle } from "lucide-react"
import { useLatestScreening, useScreeningHistory } from "@/hooks/use-api"
import { mockScreeningRuns } from "@/lib/mock-data"
import { formatDate, formatDateTime, formatNumber } from "@/lib/utils"
import type { ScreeningRun } from "@/lib/types"

interface FunnelTier {
  label: string
  count: number
  color: string
}

function buildFunnelTiers(run: ScreeningRun): FunnelTier[] {
  return [
    { label: "Tier 1: Basic Quant Filters", count: run.tier1_count, color: "#3b82f6" },
    { label: "Tier 2: Sprinkle Sauce Screens", count: run.tier2_count, color: "#2563eb" },
    { label: "Tier 3: Technical Signals", count: run.tier3_count, color: "#059669" },
    { label: "Tier 4: Wasden Watch", count: run.tier4_count, color: "#047857" },
    { label: "Tier 5: Debate + Jury", count: run.tier5_count, color: "#065f46" },
    { label: "Final: Recommendations", count: run.final_recommendations, color: "#064e3b" },
  ]
}

function FunnelVisualization({ run }: { run: ScreeningRun }) {
  const tiers = buildFunnelTiers(run)
  const maxCount = tiers[0].count

  return (
    <div className="space-y-2">
      {tiers.map((tier, index) => {
        const widthPct = Math.max((tier.count / maxCount) * 100, 8)
        const isLast = index === tiers.length - 1

        return (
          <div key={tier.label}>
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <div
                  className="relative rounded-md transition-all duration-500 ease-out"
                  style={{
                    width: `${widthPct}%`,
                    backgroundColor: tier.color,
                    minWidth: "120px",
                  }}
                >
                  <div className="flex items-center justify-between px-4 py-3">
                    <span className="text-sm font-medium text-white truncate">
                      {tier.label}
                    </span>
                    <span className="text-sm font-bold text-white ml-2 shrink-0">
                      {formatNumber(tier.count)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
            {!isLast && (
              <div className="flex items-center pl-6 py-0.5">
                <ArrowDown className="h-4 w-4 text-muted-foreground" />
                <span className="text-xs text-muted-foreground ml-2">
                  {((tiers[index + 1].count / tier.count) * 100).toFixed(1)}% pass rate
                </span>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return `${mins}m ${secs}s`
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-8 w-16" />
            </CardHeader>
          </Card>
        ))}
      </div>
      <Card>
        <CardContent className="pt-6">
          <div className="space-y-4">
            {[100, 85, 60, 40, 20, 10].map((w, i) => (
              <Skeleton key={i} className="h-12" style={{ width: `${w}%` }} />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default function ScreeningPage() {
  const { data: apiLatest, isLoading: latestLoading } = useLatestScreening()
  const { data: apiHistory, isLoading: historyLoading } = useScreeningHistory()

  const allRuns = apiHistory ?? mockScreeningRuns
  const latestRun = apiLatest ?? allRuns[0] ?? null

  const isLoading = latestLoading || historyLoading

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Filter className="h-8 w-8" />
            Screening Funnel
          </h1>
          <p className="text-muted-foreground mt-1">
            Visualize how the 5-tier screening pipeline filters stocks from universe to final recommendations.
          </p>
        </div>

        {isLoading ? (
          <LoadingSkeleton />
        ) : latestRun === null ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Filter className="mx-auto h-12 w-12 text-muted-foreground mb-3" />
              <p className="text-muted-foreground">No screening runs available</p>
            </CardContent>
          </Card>
        ) : (
          <>
            {/* Latest Run Stats */}
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardHeader className="pb-2">
                  <CardDescription className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    Latest Run Date
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <span className="text-xl font-bold">
                    {formatDateTime(latestRun.run_date)}
                  </span>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardDescription className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    Duration
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <span className="text-xl font-bold">
                    {formatDuration(latestRun.duration_seconds)}
                  </span>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardDescription className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3" />
                    Final Recommendations
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-2">
                    <span className="text-3xl font-bold text-emerald-500">
                      {latestRun.final_recommendations}
                    </span>
                    <span className="text-sm text-muted-foreground">
                      of {formatNumber(latestRun.tier1_count)} screened
                    </span>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Funnel Visualization */}
            <Card>
              <CardHeader>
                <CardTitle>Pipeline Funnel</CardTitle>
                <CardDescription>
                  Screening pipeline from {formatNumber(latestRun.tier1_count)} stocks down to{" "}
                  {latestRun.final_recommendations} recommendations
                </CardDescription>
              </CardHeader>
              <CardContent>
                <FunnelVisualization run={latestRun} />
              </CardContent>
            </Card>

            {/* Historical Runs Table */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Historical Runs</CardTitle>
                <CardDescription>All screening pipeline executions</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead className="text-center">Tier 1</TableHead>
                      <TableHead className="text-center">Tier 2</TableHead>
                      <TableHead className="text-center">Tier 3</TableHead>
                      <TableHead className="text-center">Tier 4</TableHead>
                      <TableHead className="text-center">Tier 5</TableHead>
                      <TableHead className="text-center">Final</TableHead>
                      <TableHead className="text-center">Duration</TableHead>
                      <TableHead className="text-center">Pass Rate</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {allRuns.map((run) => {
                      const overallPassRate =
                        ((run.final_recommendations / run.tier1_count) * 100).toFixed(2)
                      return (
                        <TableRow key={run.id}>
                          <TableCell className="whitespace-nowrap text-sm">
                            {formatDateTime(run.run_date)}
                          </TableCell>
                          <TableCell className="text-center font-medium">
                            {formatNumber(run.tier1_count)}
                          </TableCell>
                          <TableCell className="text-center">{run.tier2_count}</TableCell>
                          <TableCell className="text-center">{run.tier3_count}</TableCell>
                          <TableCell className="text-center">{run.tier4_count}</TableCell>
                          <TableCell className="text-center">{run.tier5_count}</TableCell>
                          <TableCell className="text-center">
                            <Badge className="bg-emerald-600 hover:bg-emerald-700">
                              {run.final_recommendations}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-center text-sm text-muted-foreground">
                            {formatDuration(run.duration_seconds)}
                          </TableCell>
                          <TableCell className="text-center text-sm text-muted-foreground">
                            {overallPassRate}%
                          </TableCell>
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
    </DashboardShell>
  )
}
