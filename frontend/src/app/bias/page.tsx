"use client"

import { DashboardShell } from "@/components/dashboard-shell"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table"
import { Skeleton } from "@/components/ui/skeleton"
import { Eye, Target, BarChart3, TrendingUp } from "lucide-react"
import { useBiasMetrics, useBiasHistory } from "@/hooks/use-api"
import { mockBiasMetrics } from "@/lib/mock-data"
import { formatDate, formatPercent } from "@/lib/utils"
import type { BiasMetric } from "@/lib/types"
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  LineChart,
  Line,
} from "recharts"

const VERDICT_COLORS = {
  APPROVE: "#10b981",
  NEUTRAL: "#f59e0b",
  VETO: "#ef4444",
}

function aggregateMetrics(metrics: BiasMetric[]) {
  const totalApprove = metrics.reduce((s, m) => s + m.approve_count, 0)
  const totalNeutral = metrics.reduce((s, m) => s + m.neutral_count, 0)
  const totalVeto = metrics.reduce((s, m) => s + m.veto_count, 0)
  const totalRecs = metrics.reduce((s, m) => s + m.total_recommendations, 0)
  const avgConfidence =
    metrics.length > 0 ? metrics.reduce((s, m) => s + m.avg_confidence, 0) / metrics.length : 0
  const totalOverrides = metrics.reduce((s, m) => s + m.override_count, 0)

  return { totalApprove, totalNeutral, totalVeto, totalRecs, avgConfidence, totalOverrides }
}

function aggregateSectors(metrics: BiasMetric[]): { name: string; count: number }[] {
  const sectorMap: Record<string, number> = {}
  for (const m of metrics) {
    for (const [sector, count] of Object.entries(m.sector_distribution)) {
      sectorMap[sector] = (sectorMap[sector] || 0) + count
    }
  }
  return Object.entries(sectorMap)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
}

const SECTOR_COLORS = ["#3b82f6", "#8b5cf6", "#ec4899", "#f97316", "#14b8a6", "#6366f1", "#eab308"]

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
      <div className="grid gap-4 md:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <Card key={i}>
            <CardContent className="pt-6">
              <Skeleton className="h-[250px] w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

export default function BiasPage() {
  const { data: apiLatest, isLoading: latestLoading } = useBiasMetrics()
  const { data: apiHistory, isLoading: historyLoading } = useBiasHistory()

  // useBiasMetrics returns a single BiasMetric, useBiasHistory returns BiasMetric[]
  // Fall back to mock data array for the full history
  const metrics = apiHistory ?? mockBiasMetrics

  const isLoading = latestLoading || historyLoading

  const { totalApprove, totalNeutral, totalVeto, totalRecs, avgConfidence, totalOverrides } =
    aggregateMetrics(metrics)

  const verdictData = [
    { name: "APPROVE", value: totalApprove },
    { name: "NEUTRAL", value: totalNeutral },
    { name: "VETO", value: totalVeto },
  ]

  const sectorData = aggregateSectors(metrics)

  const agreementData = metrics
    .slice()
    .reverse()
    .map((m) => ({
      week: formatDate(m.week_start),
      rate: Math.round(m.model_agreement_rate * 100),
    }))

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Eye className="h-8 w-8" />
            Bias Monitoring
          </h1>
          <p className="text-muted-foreground mt-1">
            Track verdict distribution, sector concentration, and model agreement to detect systematic bias.
          </p>
        </div>

        {isLoading ? (
          <LoadingSkeleton />
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardHeader className="pb-2">
                  <CardDescription className="flex items-center gap-1">
                    <Target className="h-3 w-3" />
                    Avg Confidence
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <span className="text-3xl font-bold">
                    {(avgConfidence * 100).toFixed(1)}%
                  </span>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardDescription className="flex items-center gap-1">
                    <BarChart3 className="h-3 w-3" />
                    Total Recommendations
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <span className="text-3xl font-bold">{totalRecs}</span>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardDescription className="flex items-center gap-1">
                    <TrendingUp className="h-3 w-3" />
                    Override Count
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <span className="text-3xl font-bold">{totalOverrides}</span>
                </CardContent>
              </Card>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              {/* Verdict Distribution Pie Chart */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Verdict Distribution</CardTitle>
                  <CardDescription>APPROVE / NEUTRAL / VETO breakdown</CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={260}>
                    <PieChart>
                      <Pie
                        data={verdictData}
                        cx="50%"
                        cy="50%"
                        innerRadius={55}
                        outerRadius={90}
                        paddingAngle={3}
                        dataKey="value"
                        label={({ name, percent }: { name?: string; percent?: number }) =>
                          `${name ?? ""} ${((percent ?? 0) * 100).toFixed(0)}%`
                        }
                        labelLine={false}
                      >
                        {verdictData.map((entry) => (
                          <Cell
                            key={entry.name}
                            fill={VERDICT_COLORS[entry.name as keyof typeof VERDICT_COLORS]}
                          />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                        }}
                      />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              {/* Sector Concentration Bar Chart */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Sector Concentration</CardTitle>
                  <CardDescription>Distribution across sectors</CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={sectorData} layout="vertical" margin={{ left: 10 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis type="number" tick={{ fontSize: 12 }} />
                      <YAxis
                        type="category"
                        dataKey="name"
                        tick={{ fontSize: 11 }}
                        width={120}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                        }}
                      />
                      <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                        {sectorData.map((_, index) => (
                          <Cell
                            key={index}
                            fill={SECTOR_COLORS[index % SECTOR_COLORS.length]}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              {/* Model Agreement Rate Line Chart */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Model Agreement Rate</CardTitle>
                  <CardDescription>Weekly trend over time</CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={260}>
                    <LineChart data={agreementData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="week" tick={{ fontSize: 11 }} />
                      <YAxis
                        domain={[50, 100]}
                        tick={{ fontSize: 12 }}
                        tickFormatter={(v) => `${v}%`}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                        }}
                        formatter={(value: number | undefined) => [`${value ?? 0}%`, "Agreement Rate"]}
                      />
                      <Line
                        type="monotone"
                        dataKey="rate"
                        stroke="#3b82f6"
                        strokeWidth={2}
                        dot={{ r: 4, fill: "#3b82f6" }}
                        activeDot={{ r: 6 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </div>

            {/* Weekly Data Table */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Weekly Breakdown</CardTitle>
                <CardDescription>Detailed metrics by week</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Week</TableHead>
                      <TableHead className="text-center">Approve</TableHead>
                      <TableHead className="text-center">Neutral</TableHead>
                      <TableHead className="text-center">Veto</TableHead>
                      <TableHead className="text-center">Total</TableHead>
                      <TableHead className="text-center">Agreement</TableHead>
                      <TableHead className="text-center">Avg Confidence</TableHead>
                      <TableHead className="text-center">Overrides</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {metrics.map((m) => (
                      <TableRow key={m.id}>
                        <TableCell className="text-sm whitespace-nowrap">
                          {formatDate(m.week_start)} - {formatDate(m.week_end)}
                        </TableCell>
                        <TableCell className="text-center text-emerald-500 font-medium">
                          {m.approve_count}
                        </TableCell>
                        <TableCell className="text-center text-amber-500 font-medium">
                          {m.neutral_count}
                        </TableCell>
                        <TableCell className="text-center text-red-500 font-medium">
                          {m.veto_count}
                        </TableCell>
                        <TableCell className="text-center font-medium">
                          {m.total_recommendations}
                        </TableCell>
                        <TableCell className="text-center">
                          {(m.model_agreement_rate * 100).toFixed(0)}%
                        </TableCell>
                        <TableCell className="text-center">
                          {(m.avg_confidence * 100).toFixed(1)}%
                        </TableCell>
                        <TableCell className="text-center">
                          {m.override_count}
                        </TableCell>
                      </TableRow>
                    ))}
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
