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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useJournal } from "@/hooks/use-api"
import { mockJournalEntries } from "@/lib/mock-data"
import {
  formatDate,
  formatDateTime,
  formatCurrency,
  formatPercent,
  cn,
} from "@/lib/utils"
import type { DecisionJournalEntry } from "@/lib/types"
import {
  Search,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Shield,
  Gavel,
  FileText,
  Scale,
} from "lucide-react"

function TableSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full" />
      ))}
    </div>
  )
}

function ActionBadge({ action }: { action: string }) {
  const variant =
    action === "BUY"
      ? "success"
      : action === "SELL"
        ? "destructive"
        : action === "BLOCKED"
          ? "destructive"
          : "warning"
  return <Badge variant={variant}>{action}</Badge>
}

function VerdictBadge({ verdict }: { verdict: string }) {
  const variant =
    verdict === "APPROVE"
      ? "success"
      : verdict === "VETO"
        ? "destructive"
        : "warning"
  return <Badge variant={variant}>{verdict}</Badge>
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100)
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono font-medium">{pct}%</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-muted">
        <div
          className={cn(
            "h-1.5 rounded-full",
            pct >= 70
              ? "bg-emerald-500"
              : pct >= 40
                ? "bg-amber-500"
                : "bg-red-500"
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

function CheckResult({
  label,
  passed,
  failures,
}: {
  label: string
  passed: boolean
  failures: string[]
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2">
        {passed ? (
          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
        ) : (
          <XCircle className="h-4 w-4 text-red-500" />
        )}
        <span className="text-sm font-medium">{label}</span>
        <Badge variant={passed ? "success" : "destructive"} className="text-[10px]">
          {passed ? "PASSED" : "FAILED"}
        </Badge>
      </div>
      {!passed && failures.length > 0 && (
        <ul className="ml-6 space-y-0.5">
          {failures.map((f, i) => (
            <li key={i} className="text-xs text-red-500">
              - {f}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function JournalDetailDialog({
  entry,
  open,
  onOpenChange,
}: {
  entry: DecisionJournalEntry | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  if (!entry) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <span className="text-2xl font-bold">{entry.ticker}</span>
            <ActionBadge action={entry.final_action} />
            <span className="text-sm text-muted-foreground font-normal">
              {formatDateTime(entry.created_at)}
            </span>
          </DialogTitle>
          <DialogDescription>
            Full audit trail for pipeline run {entry.pipeline_run_id.slice(0, 8)}...
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="max-h-[65vh] pr-4">
          <div className="space-y-6">
            {/* Quant Scores */}
            <div>
              <h3 className="text-sm font-semibold flex items-center gap-2 mb-3">
                <FileText className="h-4 w-4" />
                Quant Scores
              </h3>
              <div className="space-y-2">
                <ScoreBar label="XGBoost" value={entry.quant_scores.xgboost} />
                <ScoreBar label="Elastic Net" value={entry.quant_scores.elastic_net} />
                <ScoreBar label="ARIMA" value={entry.quant_scores.arima} />
                <ScoreBar label="Sentiment" value={entry.quant_scores.sentiment} />
                <Separator className="my-2" />
                <ScoreBar label="Composite" value={entry.quant_scores.composite} />
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Std Dev</span>
                  <span className="font-mono">{entry.quant_scores.std_dev.toFixed(3)}</span>
                </div>
                {entry.quant_scores.high_disagreement_flag && (
                  <div className="flex items-center gap-1 text-xs text-amber-500">
                    <AlertTriangle className="h-3 w-3" />
                    High model disagreement detected
                  </div>
                )}
              </div>
            </div>

            <Separator />

            {/* Wasden Verdict */}
            <div>
              <h3 className="text-sm font-semibold flex items-center gap-2 mb-3">
                <Gavel className="h-4 w-4" />
                Wasden Verdict
              </h3>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <VerdictBadge verdict={entry.wasden_verdict.verdict} />
                  <span className="text-xs text-muted-foreground">
                    Confidence: {(entry.wasden_verdict.confidence * 100).toFixed(0)}%
                  </span>
                  <Badge variant="outline" className="text-[10px]">
                    {entry.wasden_verdict.mode.replace("_", " ")}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {entry.wasden_verdict.reasoning}
                </p>
                <p className="text-xs text-muted-foreground">
                  Passages retrieved: {entry.wasden_verdict.passages_retrieved}
                </p>
              </div>
            </div>

            <Separator />

            {/* Bull/Bear Summary */}
            <div>
              <h3 className="text-sm font-semibold flex items-center gap-2 mb-3">
                <Scale className="h-4 w-4" />
                Debate Summary ({entry.debate_rounds} rounds — {entry.debate_outcome})
              </h3>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
                  <h4 className="text-xs font-semibold text-emerald-500 mb-1">
                    Bull Case
                  </h4>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {entry.bull_case}
                  </p>
                </div>
                <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3">
                  <h4 className="text-xs font-semibold text-red-500 mb-1">
                    Bear Case
                  </h4>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {entry.bear_case}
                  </p>
                </div>
              </div>
            </div>

            <Separator />

            {/* Jury Results */}
            <div>
              <h3 className="text-sm font-semibold flex items-center gap-2 mb-3">
                <Shield className="h-4 w-4" />
                Jury Results
              </h3>
              {entry.jury && entry.jury.spawned ? (
                <div className="space-y-2">
                  <p className="text-xs text-muted-foreground">
                    Reason: {entry.jury.reason}
                  </p>
                  <div className="flex items-center gap-3 text-sm">
                    <Badge variant="success">
                      BUY: {entry.jury.final_count.buy}
                    </Badge>
                    <Badge variant="destructive">
                      SELL: {entry.jury.final_count.sell}
                    </Badge>
                    <Badge variant="warning">
                      HOLD: {entry.jury.final_count.hold}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">Decision:</span>
                    <ActionBadge action={entry.jury.decision} />
                    {entry.jury.escalated_to_human && (
                      <Badge variant="destructive" className="text-[10px]">
                        ESCALATED TO HUMAN
                      </Badge>
                    )}
                  </div>
                </div>
              ) : (
                <p className="text-xs text-muted-foreground italic">
                  Jury was not spawned for this decision.
                </p>
              )}
            </div>

            <Separator />

            {/* Risk Check */}
            <div>
              <h3 className="text-sm font-semibold mb-3">Risk Check</h3>
              <CheckResult
                label="Risk Assessment"
                passed={entry.risk_check.passed}
                failures={entry.risk_check.checks_failed}
              />
            </div>

            <Separator />

            {/* Pre-Trade Validation (SEPARATE section) */}
            <div>
              <h3 className="text-sm font-semibold mb-3">Pre-Trade Validation</h3>
              <CheckResult
                label="Pre-Trade Checks"
                passed={entry.pre_trade_validation.passed}
                failures={entry.pre_trade_validation.checks_failed}
              />
            </div>

            <Separator />

            {/* Final Decision & Execution */}
            <div>
              <h3 className="text-sm font-semibold mb-3">Final Decision & Execution</h3>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">Action:</span>
                  <ActionBadge action={entry.final_action} />
                </div>
                <p className="text-sm text-muted-foreground">
                  {entry.final_reason}
                </p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-muted-foreground">Position Size: </span>
                    <span className="font-mono">
                      {(entry.recommended_position_size * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Human Approval: </span>
                    <span>
                      {entry.human_approval_required
                        ? entry.human_approved
                          ? "Approved"
                          : entry.human_approved === false
                            ? "Rejected"
                            : "Pending"
                        : "Not Required"}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Executed: </span>
                    <span className={entry.executed ? "text-emerald-500" : "text-red-500"}>
                      {entry.executed ? "Yes" : "No"}
                    </span>
                  </div>
                  {entry.fill_price !== null && (
                    <div>
                      <span className="text-muted-foreground">Fill Price: </span>
                      <span className="font-mono">{formatCurrency(entry.fill_price)}</span>
                    </div>
                  )}
                  {entry.slippage !== null && (
                    <div>
                      <span className="text-muted-foreground">Slippage: </span>
                      <span className="font-mono">{formatPercent(entry.slippage * 100)}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  )
}

export default function JournalPage() {
  const [tickerFilter, setTickerFilter] = useState("")
  const [actionFilter, setActionFilter] = useState<string>("all")
  const [selectedEntry, setSelectedEntry] = useState<DecisionJournalEntry | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)

  const { data: apiEntries, isLoading } = useJournal()
  const entries = apiEntries ?? mockJournalEntries

  const filtered = entries.filter((entry) => {
    const matchesTicker =
      !tickerFilter ||
      entry.ticker.toLowerCase().includes(tickerFilter.toLowerCase())
    const matchesAction =
      actionFilter === "all" || entry.final_action === actionFilter
    return matchesTicker && matchesAction
  })

  function handleRowClick(entry: DecisionJournalEntry) {
    setSelectedEntry(entry)
    setDialogOpen(true)
  }

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Decision Journal</h1>
          <p className="text-muted-foreground">
            Full audit trail for every pipeline decision
          </p>
        </div>

        {/* Filter Bar */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-wrap items-center gap-4">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Filter by ticker..."
                  value={tickerFilter}
                  onChange={(e) => setTickerFilter(e.target.value)}
                  className="pl-9"
                />
              </div>
              <Select value={actionFilter} onValueChange={setActionFilter}>
                <SelectTrigger className="w-[160px]">
                  <SelectValue placeholder="Action" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Actions</SelectItem>
                  <SelectItem value="BUY">BUY</SelectItem>
                  <SelectItem value="SELL">SELL</SelectItem>
                  <SelectItem value="HOLD">HOLD</SelectItem>
                  <SelectItem value="BLOCKED">BLOCKED</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Journal Table */}
        <Card>
          <CardHeader>
            <CardTitle>Journal Entries</CardTitle>
            <CardDescription>
              Click a row to view the full audit trail
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <TableSkeleton />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Ticker</TableHead>
                    <TableHead>Wasden Verdict</TableHead>
                    <TableHead className="text-right">Quant Score</TableHead>
                    <TableHead>Debate</TableHead>
                    <TableHead>Final Action</TableHead>
                    <TableHead>Executed</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.length === 0 ? (
                    <TableRow>
                      <TableCell
                        colSpan={7}
                        className="text-center text-muted-foreground py-8"
                      >
                        No journal entries match the filters.
                      </TableCell>
                    </TableRow>
                  ) : (
                    filtered.map((entry) => (
                      <TableRow
                        key={entry.id}
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => handleRowClick(entry)}
                      >
                        <TableCell className="text-sm">
                          {formatDate(entry.created_at)}
                        </TableCell>
                        <TableCell className="font-semibold">
                          {entry.ticker}
                        </TableCell>
                        <TableCell>
                          <VerdictBadge verdict={entry.wasden_verdict.verdict} />
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {(entry.quant_scores.composite * 100).toFixed(0)}%
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              entry.debate_outcome === "agreement"
                                ? "secondary"
                                : "warning"
                            }
                          >
                            {entry.debate_outcome} ({entry.debate_rounds}R)
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <ActionBadge action={entry.final_action} />
                        </TableCell>
                        <TableCell>
                          {entry.executed ? (
                            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                          ) : (
                            <XCircle className="h-4 w-4 text-red-500" />
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Detail Dialog */}
        <JournalDetailDialog
          entry={selectedEntry}
          open={dialogOpen}
          onOpenChange={setDialogOpen}
        />
      </div>
    </DashboardShell>
  )
}
