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
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Skeleton } from "@/components/ui/skeleton"
import { usePositions, usePnL, usePortfolioSummary } from "@/hooks/use-api"
import {
  mockPositions,
  mockPnL,
  mockSummary,
} from "@/lib/mock-data"
import {
  formatCurrency,
  formatPercent,
  formatDate,
  cn,
} from "@/lib/utils"
import type { PortfolioPosition } from "@/lib/types"
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  Activity,
  Target,
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
} from "recharts"

function StatCardSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-4 rounded" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-32 mb-1" />
        <Skeleton className="h-3 w-20" />
      </CardContent>
    </Card>
  )
}

function TableSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  )
}

function ChartSkeleton() {
  return <Skeleton className="h-[350px] w-full" />
}

function PositionsTable({ positions }: { positions: PortfolioPosition[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Ticker</TableHead>
          <TableHead>Direction</TableHead>
          <TableHead className="text-right">Entry Price</TableHead>
          <TableHead className="text-right">
            {positions[0]?.status === "open" ? "Current Price" : "Exit Price"}
          </TableHead>
          <TableHead className="text-right">Shares</TableHead>
          <TableHead className="text-right">P&L</TableHead>
          <TableHead className="text-right">P&L %</TableHead>
          <TableHead>Status</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {positions.length === 0 ? (
          <TableRow>
            <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
              No positions found
            </TableCell>
          </TableRow>
        ) : (
          positions.map((pos) => (
            <TableRow key={pos.id}>
              <TableCell className="font-semibold">{pos.ticker}</TableCell>
              <TableCell>
                <Badge variant={pos.direction === "long" ? "success" : "destructive"}>
                  {pos.direction.toUpperCase()}
                </Badge>
              </TableCell>
              <TableCell className="text-right font-mono">
                {formatCurrency(pos.entry_price)}
              </TableCell>
              <TableCell className="text-right font-mono">
                {formatCurrency(pos.status === "closed" && pos.exit_price ? pos.exit_price : pos.current_price)}
              </TableCell>
              <TableCell className="text-right">{pos.shares}</TableCell>
              <TableCell
                className={cn(
                  "text-right font-mono font-medium",
                  pos.pnl >= 0 ? "text-emerald-500" : "text-red-500"
                )}
              >
                {formatCurrency(pos.pnl)}
              </TableCell>
              <TableCell
                className={cn(
                  "text-right font-mono font-medium",
                  pos.pnl_pct >= 0 ? "text-emerald-500" : "text-red-500"
                )}
              >
                {formatPercent(pos.pnl_pct)}
              </TableCell>
              <TableCell>
                <Badge variant={pos.status === "open" ? "default" : "secondary"}>
                  {pos.status.toUpperCase()}
                </Badge>
              </TableCell>
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  )
}

export default function PortfolioPage() {
  const { data: apiSummary, isLoading: summaryLoading } = usePortfolioSummary()
  const { data: apiPnL, isLoading: pnlLoading } = usePnL()
  const { data: apiPositions, isLoading: positionsLoading } = usePositions()

  const summary = apiSummary ?? mockSummary
  const pnl = apiPnL ?? mockPnL
  const positions = apiPositions ?? mockPositions

  const [tab, setTab] = useState("open")

  const openPositions = positions.filter((p) => p.status === "open")
  const closedPositions = positions.filter((p) => p.status === "closed")

  const chartData = pnl.map((day) => ({
    date: formatDate(day.date),
    "Portfolio P&L": Number(day.cumulative_pnl.toFixed(2)),
    "SPY Return": Number((day.spy_cumulative_return * 1000).toFixed(2)),
  }))

  const statCards = [
    {
      title: "Total Value",
      value: formatCurrency(summary.total_value),
      description: `${summary.open_positions} open, ${summary.closed_positions} closed`,
      icon: DollarSign,
      trend: null,
    },
    {
      title: "Daily P&L",
      value: formatCurrency(summary.daily_pnl),
      description: formatPercent(summary.daily_pnl_pct),
      icon: summary.daily_pnl >= 0 ? TrendingUp : TrendingDown,
      trend: summary.daily_pnl >= 0 ? "up" : "down",
    },
    {
      title: "Total P&L",
      value: formatCurrency(summary.total_pnl),
      description: formatPercent(summary.total_pnl_pct),
      icon: summary.total_pnl >= 0 ? TrendingUp : TrendingDown,
      trend: summary.total_pnl >= 0 ? "up" : "down",
    },
    {
      title: "Win Rate",
      value: `${summary.win_rate.toFixed(1)}%`,
      description: `Cash: ${formatCurrency(summary.cash_balance)}`,
      icon: Target,
      trend: summary.win_rate >= 50 ? "up" : "down",
    },
  ]

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Portfolio</h1>
          <p className="text-muted-foreground">
            Monitor positions, P&L, and portfolio performance
          </p>
        </div>

        {/* Summary Stat Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {summaryLoading
            ? Array.from({ length: 4 }).map((_, i) => <StatCardSkeleton key={i} />)
            : statCards.map((card) => (
                <Card key={card.title}>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      {card.title}
                    </CardTitle>
                    <card.icon
                      className={cn(
                        "h-4 w-4",
                        card.trend === "up"
                          ? "text-emerald-500"
                          : card.trend === "down"
                            ? "text-red-500"
                            : "text-muted-foreground"
                      )}
                    />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{card.value}</div>
                    <p
                      className={cn(
                        "text-xs",
                        card.trend === "up"
                          ? "text-emerald-500"
                          : card.trend === "down"
                            ? "text-red-500"
                            : "text-muted-foreground"
                      )}
                    >
                      {card.description}
                    </p>
                  </CardContent>
                </Card>
              ))}
        </div>

        {/* P&L vs SPY Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Portfolio P&L vs SPY</CardTitle>
            <CardDescription>
              Cumulative performance comparison over the last 30 days
            </CardDescription>
          </CardHeader>
          <CardContent>
            {pnlLoading ? (
              <ChartSkeleton />
            ) : (
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 12 }}
                    className="text-muted-foreground"
                  />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    className="text-muted-foreground"
                    tickFormatter={(val) => `$${val}`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                    labelStyle={{ color: "hsl(var(--foreground))" }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="Portfolio P&L"
                    stroke="#10b981"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="SPY Return"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Positions Table */}
        <Card>
          <CardHeader>
            <CardTitle>Positions</CardTitle>
            <CardDescription>
              All portfolio positions with P&L tracking
            </CardDescription>
          </CardHeader>
          <CardContent>
            {positionsLoading ? (
              <TableSkeleton />
            ) : (
              <Tabs value={tab} onValueChange={setTab}>
                <TabsList>
                  <TabsTrigger value="open">
                    Open ({openPositions.length})
                  </TabsTrigger>
                  <TabsTrigger value="closed">
                    Closed ({closedPositions.length})
                  </TabsTrigger>
                </TabsList>
                <TabsContent value="open" className="mt-4">
                  <PositionsTable positions={openPositions} />
                </TabsContent>
                <TabsContent value="closed" className="mt-4">
                  <PositionsTable positions={closedPositions} />
                </TabsContent>
              </Tabs>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardShell>
  )
}
