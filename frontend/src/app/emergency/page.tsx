"use client"

import { useState } from "react"
import { DashboardShell } from "@/components/dashboard-shell"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table"
import { Skeleton } from "@/components/ui/skeleton"
import { Separator } from "@/components/ui/separator"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  ShieldOff,
  Power,
  PlayCircle,
  XCircle,
  FileText,
} from "lucide-react"
import { useEmergencyStatus, useShutdownHistory } from "@/hooks/use-api"
import { mockEmergencyStatus, mockShutdownHistory } from "@/lib/mock-data"
import { formatDateTime } from "@/lib/utils"
import type { EmergencyStatus, ShutdownEvent } from "@/lib/types"

type ActionType = "shutdown" | "resume" | "cancel_orders" | "force_paper"

const ACTION_CONFIG: Record<ActionType, { title: string; description: string }> = {
  shutdown: {
    title: "Emergency Shutdown",
    description: "This will immediately halt all trading activity, cancel pending orders, and prevent new orders from being placed.",
  },
  resume: {
    title: "Resume Trading",
    description: "This will resume normal trading operations. Ensure all conditions are safe before proceeding.",
  },
  cancel_orders: {
    title: "Cancel All Orders",
    description: "This will cancel all pending and open orders. Existing positions will remain unchanged.",
  },
  force_paper: {
    title: "Force Paper Mode",
    description: "This will switch the system to paper trading mode. No real orders will be executed.",
  },
}

function eventTypeBadge(eventType: ShutdownEvent["event_type"]) {
  switch (eventType) {
    case "shutdown":
      return <Badge variant="destructive">Shutdown</Badge>
    case "resume":
      return <Badge className="bg-emerald-600 hover:bg-emerald-700">Resume</Badge>
    case "cancel_orders":
      return <Badge className="bg-amber-600 hover:bg-amber-700">Cancel Orders</Badge>
    case "force_paper":
      return <Badge className="bg-blue-600 hover:bg-blue-700">Force Paper</Badge>
  }
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-28 w-full" />
      <div className="grid gap-4 md:grid-cols-2">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-5 w-40" />
              <Skeleton className="h-4 w-56" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-10 w-32" />
            </CardContent>
          </Card>
        ))}
      </div>
      <Card>
        <CardContent className="py-6 space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

export default function EmergencyPage() {
  const { data: apiStatus, isLoading: statusLoading } = useEmergencyStatus()
  const { data: apiHistory, isLoading: historyLoading } = useShutdownHistory()

  const status = apiStatus ?? mockEmergencyStatus
  const history = apiHistory ?? mockShutdownHistory

  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogAction, setDialogAction] = useState<ActionType>("shutdown")
  const [initiatedBy, setInitiatedBy] = useState("")
  const [reason, setReason] = useState("")

  const isLoading = statusLoading || historyLoading

  const openDialog = (action: ActionType) => {
    setDialogAction(action)
    setInitiatedBy("")
    setReason("")
    setDialogOpen(true)
  }

  const handleConfirm = () => {
    console.log(`${dialogAction}:`, { initiated_by: initiatedBy, reason })
    setDialogOpen(false)
    setInitiatedBy("")
    setReason("")
  }

  const config = ACTION_CONFIG[dialogAction]

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <ShieldOff className="h-8 w-8" />
            Emergency Controls
          </h1>
          <p className="text-muted-foreground mt-1">
            Emergency shutdown, resume trading, and crisis management tools.
          </p>
        </div>

        {isLoading ? (
          <LoadingSkeleton />
        ) : (
          <>
            {/* Status Banner */}
            {status.is_shutdown ? (
              <Card className="border-red-500 bg-red-500/10">
                <CardContent className="py-6">
                  <div className="flex items-center gap-3">
                    <span className="relative flex h-4 w-4">
                      <span className="absolute inline-flex h-full w-full rounded-full bg-red-500 opacity-75 animate-pulse" />
                      <span className="relative inline-flex h-4 w-4 rounded-full bg-red-500" />
                    </span>
                    <span className="text-2xl font-bold text-red-500">SHUTDOWN ACTIVE</span>
                    <Badge variant="outline">{status.trading_mode}</Badge>
                  </div>
                  <div className="mt-3 space-y-1 text-sm text-muted-foreground">
                    {status.initiated_by && <p>Initiated by: <span className="font-medium text-foreground">{status.initiated_by}</span></p>}
                    {status.reason && <p>Reason: <span className="font-medium text-foreground">{status.reason}</span></p>}
                    {status.shutdown_at && <p>Shutdown at: <span className="font-medium text-foreground">{formatDateTime(status.shutdown_at)}</span></p>}
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card className="border-emerald-500 bg-emerald-500/10">
                <CardContent className="py-6">
                  <div className="flex items-center gap-3">
                    <span className="relative flex h-4 w-4">
                      <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75 animate-pulse" />
                      <span className="relative inline-flex h-4 w-4 rounded-full bg-emerald-500" />
                    </span>
                    <span className="text-2xl font-bold text-emerald-500">TRADING ACTIVE</span>
                    <Badge variant="outline">{status.trading_mode}</Badge>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Action Cards */}
            <div className="grid gap-4 md:grid-cols-2">
              <Card className="border-red-500/50">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-red-500">
                    <Power className="h-5 w-5" />
                    Emergency Shutdown
                  </CardTitle>
                  <CardDescription>Immediately halt all trading activity</CardDescription>
                </CardHeader>
                <CardContent>
                  <Button variant="destructive" onClick={() => openDialog("shutdown")}>
                    Activate Shutdown
                  </Button>
                </CardContent>
              </Card>

              <Card className="border-emerald-500/50">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-emerald-500">
                    <PlayCircle className="h-5 w-5" />
                    Resume Trading
                  </CardTitle>
                  <CardDescription>Resume normal trading operations</CardDescription>
                </CardHeader>
                <CardContent>
                  <Button className="bg-emerald-600 hover:bg-emerald-700" onClick={() => openDialog("resume")}>
                    Resume Trading
                  </Button>
                </CardContent>
              </Card>

              <Card className="border-amber-500/50">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-amber-500">
                    <XCircle className="h-5 w-5" />
                    Cancel All Orders
                  </CardTitle>
                  <CardDescription>Cancel all pending and open orders</CardDescription>
                </CardHeader>
                <CardContent>
                  <Button className="bg-amber-600 hover:bg-amber-700" onClick={() => openDialog("cancel_orders")}>
                    Cancel Orders
                  </Button>
                </CardContent>
              </Card>

              <Card className="border-blue-500/50">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-blue-500">
                    <FileText className="h-5 w-5" />
                    Force Paper Mode
                  </CardTitle>
                  <CardDescription>Switch system to paper trading mode</CardDescription>
                </CardHeader>
                <CardContent>
                  <Button className="bg-blue-600 hover:bg-blue-700" onClick={() => openDialog("force_paper")}>
                    Force Paper Mode
                  </Button>
                </CardContent>
              </Card>
            </div>

            {/* Confirmation Dialog */}
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>{config.title}</DialogTitle>
                  <DialogDescription>{config.description}</DialogDescription>
                </DialogHeader>
                <div className="space-y-4 pt-2">
                  <div>
                    <Label htmlFor="initiated-by">Initiated By</Label>
                    <Input
                      id="initiated-by"
                      placeholder="Your name"
                      value={initiatedBy}
                      onChange={(e) => setInitiatedBy(e.target.value)}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="reason">Reason</Label>
                    <Textarea
                      id="reason"
                      placeholder="Provide a reason for this action..."
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      className="mt-1"
                    />
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <Button variant="outline" onClick={() => setDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button
                      onClick={handleConfirm}
                      disabled={!initiatedBy.trim() || !reason.trim()}
                      variant={dialogAction === "shutdown" ? "destructive" : "default"}
                    >
                      Confirm
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>

            <Separator />

            {/* Event History Table */}
            <div className="space-y-4">
              <h2 className="text-xl font-semibold">Event History</h2>
              <Card>
                <CardContent className="p-0">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Time</TableHead>
                        <TableHead>Event Type</TableHead>
                        <TableHead>Initiated By</TableHead>
                        <TableHead>Reason</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {history.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                            No emergency events recorded
                          </TableCell>
                        </TableRow>
                      ) : (
                        history.map((event) => (
                          <TableRow key={event.id}>
                            <TableCell className="whitespace-nowrap text-sm">
                              {formatDateTime(event.created_at)}
                            </TableCell>
                            <TableCell>{eventTypeBadge(event.event_type)}</TableCell>
                            <TableCell className="font-medium">{event.initiated_by}</TableCell>
                            <TableCell className="text-sm">{event.reason}</TableCell>
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
