"use client"

import { useState } from "react"
import { DashboardShell } from "@/components/dashboard-shell"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table"
import { Skeleton } from "@/components/ui/skeleton"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert"
import { Scale, AlertTriangle, ArrowUpDown, Eye, Play } from "lucide-react"
import { useDrift, useTargets } from "@/hooks/use-api"
import { mockDrift, mockTargets } from "@/lib/mock-data"
import { formatPercent } from "@/lib/utils"
import type { DriftAnalysis, DriftEntry, TargetWeights } from "@/lib/types"

function driftStatusBadge(status: DriftEntry["status"]) {
  switch (status) {
    case "in_range":
      return <Badge className="bg-emerald-600 hover:bg-emerald-700">In Range</Badge>
    case "over":
      return <Badge variant="destructive">Over</Badge>
    case "under":
      return <Badge className="bg-amber-600 hover:bg-amber-700">Under</Badge>
  }
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
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </CardContent>
      </Card>
      <Card>
        <CardContent className="py-6 space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

const samplePreviewTrades = [
  { ticker: "NVDA", action: "SELL", shares: 5, estimated_value: 949.10 },
  { ticker: "AAPL", action: "BUY", shares: 8, estimated_value: 2116.64 },
  { ticker: "AMD", action: "SELL", shares: 6, estimated_value: 1200.90 },
  { ticker: "XOM", action: "BUY", shares: 10, estimated_value: 1472.80 },
]

export default function RebalancingPage() {
  const { data: apiDrift, isLoading: driftLoading } = useDrift()
  const { data: apiTargets, isLoading: targetsLoading } = useTargets()

  const drift: DriftAnalysis = apiDrift ?? mockDrift
  const targets: TargetWeights = apiTargets ?? mockTargets

  const isLoading = driftLoading || targetsLoading

  const [editedWeights, setEditedWeights] = useState<Record<string, number>>({})
  const [showPreview, setShowPreview] = useState(false)
  const [executeConfirmed, setExecuteConfirmed] = useState(false)

  const handleWeightChange = (ticker: string, value: string) => {
    const num = parseFloat(value)
    if (!isNaN(num)) {
      setEditedWeights((prev) => ({ ...prev, [ticker]: num }))
    }
  }

  const handleSaveTargets = () => {
    const merged = { ...targets.weights, ...editedWeights }
    console.log("Saving target weights:", merged)
  }

  const handleExecuteRebalance = () => {
    if (!executeConfirmed) {
      setExecuteConfirmed(true)
      return
    }
    console.log("Executing rebalance trades...")
    setExecuteConfirmed(false)
  }

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Scale className="h-8 w-8" />
            Portfolio Rebalancing
          </h1>
          <p className="text-muted-foreground mt-1">
            Monitor portfolio drift and execute rebalancing trades.
          </p>
        </div>

        {drift.rebalance_needed && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Rebalance Needed</AlertTitle>
            <AlertDescription>
              Total portfolio drift is {drift.total_drift.toFixed(1)}%. One or more positions have
              drifted beyond acceptable thresholds. Review the drift table below and consider
              rebalancing.
            </AlertDescription>
          </Alert>
        )}

        {isLoading ? (
          <LoadingSkeleton />
        ) : (
          <>
            {/* Stat Cards */}
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardHeader className="pb-2">
                  <CardDescription className="flex items-center gap-1">
                    <ArrowUpDown className="h-3 w-3" />
                    Total Drift
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <span
                    className={`text-3xl font-bold ${
                      drift.total_drift > 5 ? "text-red-500" : "text-emerald-500"
                    }`}
                  >
                    {drift.total_drift.toFixed(1)}%
                  </span>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardDescription>Positions Tracked</CardDescription>
                </CardHeader>
                <CardContent>
                  <span className="text-3xl font-bold">{drift.positions.length}</span>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardDescription>Rebalance Needed</CardDescription>
                </CardHeader>
                <CardContent>
                  {drift.rebalance_needed ? (
                    <Badge variant="destructive" className="text-lg px-3 py-1">Yes</Badge>
                  ) : (
                    <Badge className="bg-emerald-600 hover:bg-emerald-700 text-lg px-3 py-1">No</Badge>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Drift Table */}
            <Card>
              <CardHeader>
                <CardTitle>Position Drift</CardTitle>
                <CardDescription>
                  Current allocation vs target weights for each position
                </CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Ticker</TableHead>
                      <TableHead className="text-right">Target %</TableHead>
                      <TableHead className="text-right">Current %</TableHead>
                      <TableHead className="text-right">Drift %</TableHead>
                      <TableHead className="text-center">Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {drift.positions.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                          No positions to display
                        </TableCell>
                      </TableRow>
                    ) : (
                      drift.positions.map((entry) => (
                        <TableRow key={entry.ticker}>
                          <TableCell className="font-semibold">{entry.ticker}</TableCell>
                          <TableCell className="text-right font-mono">
                            {entry.target_pct.toFixed(1)}%
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {entry.current_pct.toFixed(1)}%
                          </TableCell>
                          <TableCell
                            className={`text-right font-mono font-medium ${
                              entry.drift_pct > 0
                                ? "text-red-500"
                                : entry.drift_pct < 0
                                  ? "text-amber-500"
                                  : "text-emerald-500"
                            }`}
                          >
                            {entry.drift_pct > 0 ? "+" : ""}{entry.drift_pct.toFixed(1)}%
                          </TableCell>
                          <TableCell className="text-center">
                            {driftStatusBadge(entry.status)}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            {/* Target Editor */}
            <Card>
              <CardHeader>
                <CardTitle>Target Weights</CardTitle>
                <CardDescription>
                  Edit target allocation percentages for each ticker. Cash weight: {targets.cash_weight}%
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {Object.entries(targets.weights).map(([ticker, weight]) => (
                    <div key={ticker} className="flex items-center gap-3">
                      <Label htmlFor={`weight-${ticker}`} className="w-14 font-semibold shrink-0">
                        {ticker}
                      </Label>
                      <Input
                        id={`weight-${ticker}`}
                        type="number"
                        step="0.5"
                        min="0"
                        max="100"
                        value={editedWeights[ticker] ?? weight}
                        onChange={(e) => handleWeightChange(ticker, e.target.value)}
                        className="w-24"
                      />
                      <span className="text-sm text-muted-foreground">%</span>
                    </div>
                  ))}
                </div>
                <div className="mt-4">
                  <Button onClick={handleSaveTargets}>Save Targets</Button>
                </div>
              </CardContent>
            </Card>

            <Separator />

            {/* Action Buttons */}
            <Card>
              <CardHeader>
                <CardTitle>Rebalance Actions</CardTitle>
                <CardDescription>
                  Preview proposed trades or execute a full rebalance
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-3">
                  <Button
                    variant="outline"
                    onClick={() => setShowPreview(!showPreview)}
                  >
                    <Eye className="mr-2 h-4 w-4" />
                    {showPreview ? "Hide Preview" : "Preview Rebalance"}
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={handleExecuteRebalance}
                  >
                    <Play className="mr-2 h-4 w-4" />
                    {executeConfirmed ? "Confirm Execution" : "Execute Rebalance"}
                  </Button>
                </div>

                {executeConfirmed && (
                  <Alert variant="destructive">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertTitle>Confirm Rebalance Execution</AlertTitle>
                    <AlertDescription>
                      This will submit real trades to rebalance the portfolio. Click &quot;Confirm
                      Execution&quot; again to proceed, or click elsewhere to cancel.
                    </AlertDescription>
                  </Alert>
                )}

                {showPreview && (
                  <div className="mt-4">
                    <h3 className="text-sm font-semibold mb-2">Proposed Trades</h3>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Ticker</TableHead>
                          <TableHead>Action</TableHead>
                          <TableHead className="text-right">Shares</TableHead>
                          <TableHead className="text-right">Estimated Value</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {samplePreviewTrades.map((trade) => (
                          <TableRow key={trade.ticker}>
                            <TableCell className="font-semibold">{trade.ticker}</TableCell>
                            <TableCell>
                              <Badge
                                variant={trade.action === "BUY" ? "default" : "destructive"}
                              >
                                {trade.action}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right font-mono">{trade.shares}</TableCell>
                            <TableCell className="text-right font-mono">
                              ${trade.estimated_value.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </DashboardShell>
  )
}
