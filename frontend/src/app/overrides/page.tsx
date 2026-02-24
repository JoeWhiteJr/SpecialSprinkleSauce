"use client"

import { useState } from "react"
import { DashboardShell } from "@/components/dashboard-shell"
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { ShieldAlert, Plus, CheckCircle, XCircle, ArrowUpCircle, DollarSign } from "lucide-react"
import { useOverrides } from "@/hooks/use-api"
import { mockOverrides } from "@/lib/mock-data"
import { formatCurrency, formatDate } from "@/lib/utils"
import type { VetoOverride } from "@/lib/types"

function statusBadge(status: VetoOverride["status"]) {
  switch (status) {
    case "pending":
      return <Badge variant="outline" className="border-amber-500 text-amber-500">Pending</Badge>
    case "approved":
      return <Badge className="bg-emerald-600 hover:bg-emerald-700">Approved</Badge>
    case "rejected":
      return <Badge variant="destructive">Rejected</Badge>
    case "completed":
      return <Badge className="bg-blue-600 hover:bg-blue-700">Completed</Badge>
  }
}

function OverrideCard({
  override,
  showActions,
}: {
  override: VetoOverride
  showActions: boolean
}) {
  const [reason, setReason] = useState("")
  const [actionTaken, setActionTaken] = useState<string | null>(null)

  const handleAction = (action: string) => {
    if (!reason.trim()) return
    setActionTaken(action)
    // In production, this would call an API endpoint
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CardTitle className="text-lg">{override.ticker}</CardTitle>
            {statusBadge(override.status)}
          </div>
          <span className="text-sm text-muted-foreground">
            {formatDate(override.created_at)}
          </span>
        </div>
        <CardDescription>
          Original Verdict: <span className="font-semibold text-red-400">{override.original_verdict}</span>
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <p className="text-sm font-medium text-muted-foreground mb-1">Override Reason</p>
          <p className="text-sm">{override.override_reason}</p>
        </div>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span>Overridden by: <span className="font-medium text-foreground">{override.overridden_by}</span></span>
        </div>

        {override.outcome_tracked && override.outcome_pnl !== null && (
          <>
            <Separator />
            <div className="flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Outcome P&L:</span>
              <span
                className={`text-sm font-bold ${
                  override.outcome_pnl >= 0 ? "text-emerald-500" : "text-red-500"
                }`}
              >
                {formatCurrency(override.outcome_pnl)}
              </span>
            </div>
            {override.outcome_note && (
              <p className="text-sm text-muted-foreground">{override.outcome_note}</p>
            )}
          </>
        )}

        {override.status === "rejected" && override.outcome_note && (
          <>
            <Separator />
            <p className="text-sm text-muted-foreground">{override.outcome_note}</p>
          </>
        )}

        {showActions && !actionTaken && (
          <>
            <Separator />
            <div className="space-y-3">
              <div>
                <Label htmlFor={`reason-${override.id}`} className="text-sm">
                  Decision Reason <span className="text-red-500">*</span>
                </Label>
                <textarea
                  id={`reason-${override.id}`}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Provide reasoning for your decision..."
                  className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm min-h-[80px] resize-none focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  className="bg-emerald-600 hover:bg-emerald-700"
                  onClick={() => handleAction("approve")}
                  disabled={!reason.trim()}
                >
                  <CheckCircle className="mr-1 h-4 w-4" />
                  Approve
                </Button>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => handleAction("reject")}
                  disabled={!reason.trim()}
                >
                  <XCircle className="mr-1 h-4 w-4" />
                  Reject
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleAction("escalate")}
                  disabled={!reason.trim()}
                >
                  <ArrowUpCircle className="mr-1 h-4 w-4" />
                  Escalate
                </Button>
              </div>
            </div>
          </>
        )}

        {actionTaken && (
          <>
            <Separator />
            <div className="flex items-center gap-2 text-sm text-emerald-500">
              <CheckCircle className="h-4 w-4" />
              Override {actionTaken} successfully
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}

function NewOverrideDialog() {
  const [open, setOpen] = useState(false)
  const [ticker, setTicker] = useState("")
  const [overrideReason, setOverrideReason] = useState("")
  const [overriddenBy, setOverriddenBy] = useState("")

  const handleSubmit = () => {
    if (!ticker.trim() || !overrideReason.trim() || !overriddenBy.trim()) return
    // In production, this would call createOverride API
    setOpen(false)
    setTicker("")
    setOverrideReason("")
    setOverriddenBy("")
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          New Override
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Request Veto Override</DialogTitle>
          <DialogDescription>
            Submit a request to override a Wasden Watch VETO verdict. This requires review and approval.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 pt-2">
          <div>
            <Label htmlFor="override-ticker">Ticker</Label>
            <Input
              id="override-ticker"
              placeholder="e.g. TSLA"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              className="mt-1"
            />
          </div>
          <div>
            <Label htmlFor="override-by">Requested By</Label>
            <Input
              id="override-by"
              placeholder="Your name"
              value={overriddenBy}
              onChange={(e) => setOverriddenBy(e.target.value)}
              className="mt-1"
            />
          </div>
          <div>
            <Label htmlFor="override-reason">Override Reason</Label>
            <textarea
              id="override-reason"
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
              placeholder="Explain why the VETO should be overridden..."
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm min-h-[100px] resize-none focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={!ticker.trim() || !overrideReason.trim() || !overriddenBy.trim()}
            >
              Submit Override Request
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2, 3].map((i) => (
        <Card key={i}>
          <CardHeader>
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-48" />
          </CardHeader>
          <CardContent className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export default function OverridesPage() {
  const { data: apiData, isLoading } = useOverrides()
  const overrides = apiData ?? mockOverrides

  const pending = overrides.filter((o) => o.status === "pending")
  const completed = overrides.filter((o) => o.status !== "pending")

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
              <ShieldAlert className="h-8 w-8" />
              Override Controls
            </h1>
            <p className="text-muted-foreground mt-1">
              Manage Wasden Watch veto overrides. Pending requests require review with mandatory reasoning.
            </p>
          </div>
          <NewOverrideDialog />
        </div>

        <div className="grid grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Pending</CardDescription>
              <CardTitle className="text-2xl text-amber-500">{pending.length}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Approved</CardDescription>
              <CardTitle className="text-2xl text-emerald-500">
                {overrides.filter((o) => o.status === "approved" || o.status === "completed").length}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Rejected</CardDescription>
              <CardTitle className="text-2xl text-red-500">
                {overrides.filter((o) => o.status === "rejected").length}
              </CardTitle>
            </CardHeader>
          </Card>
        </div>

        <Tabs defaultValue="pending">
          <TabsList>
            <TabsTrigger value="pending">
              Pending ({pending.length})
            </TabsTrigger>
            <TabsTrigger value="completed">
              Completed ({completed.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="pending" className="mt-4">
            {isLoading ? (
              <LoadingSkeleton />
            ) : pending.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <ShieldAlert className="mx-auto h-12 w-12 text-muted-foreground mb-3" />
                  <p className="text-muted-foreground">No pending override requests</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-4">
                {pending.map((override) => (
                  <OverrideCard key={override.id} override={override} showActions />
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="completed" className="mt-4">
            {isLoading ? (
              <LoadingSkeleton />
            ) : completed.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <p className="text-muted-foreground">No completed overrides yet</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-4">
                {completed.map((override) => (
                  <OverrideCard key={override.id} override={override} showActions={false} />
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </DashboardShell>
  )
}
