"use client"

import { useState } from "react"
import { DashboardShell } from "@/components/dashboard-shell"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table"
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Bell,
  CheckCircle,
  XCircle,
  Send,
  MessageSquare,
  Mail,
  FileText,
} from "lucide-react"
import { useNotifications, useNotificationChannels } from "@/hooks/use-api"
import { mockNotifications, mockNotificationChannels } from "@/lib/mock-data"
import { formatDateTime } from "@/lib/utils"
import type { Notification, NotificationChannel } from "@/lib/types"

function severityBadge(severity: Notification["severity"]) {
  switch (severity) {
    case "info":
      return <Badge variant="outline" className="border-blue-500 text-blue-500">Info</Badge>
    case "warning":
      return <Badge className="bg-amber-600 hover:bg-amber-700">Warning</Badge>
    case "critical":
      return <Badge variant="destructive">Critical</Badge>
  }
}

function channelIcon(type: NotificationChannel["type"]) {
  switch (type) {
    case "log":
      return <FileText className="h-5 w-5" />
    case "slack":
      return <MessageSquare className="h-5 w-5" />
    case "email":
      return <Mail className="h-5 w-5" />
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
      <div className="grid gap-4 md:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-6 w-20" />
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

export default function NotificationsPage() {
  const { data: apiNotifications, isLoading: notificationsLoading } = useNotifications()
  const { data: apiChannels, isLoading: channelsLoading } = useNotificationChannels()

  const notifications = apiNotifications ?? mockNotifications
  const channels = apiChannels ?? mockNotificationChannels

  const [severityFilter, setSeverityFilter] = useState<string>("all")

  const isLoading = notificationsLoading || channelsLoading

  const filteredNotifications = notifications.filter((n) => {
    if (severityFilter === "all") return true
    return n.severity === severityFilter
  })

  const criticalCount = notifications.filter((n) => n.severity === "critical").length
  const enabledChannelsCount = channels.filter((ch) => ch.enabled).length

  const sendTestNotification = () => {
    // Placeholder — logs to console until backend wiring is complete
    console.log("sendTestNotification: dispatching test notification to all enabled channels")
  }

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
              <Bell className="h-8 w-8" />
              Notifications
            </h1>
            <p className="text-muted-foreground mt-1">
              Monitor notification delivery across all configured channels.
            </p>
          </div>
          <Button onClick={sendTestNotification}>
            <Send className="mr-2 h-4 w-4" />
            Send Test
          </Button>
        </div>

        {isLoading ? (
          <LoadingSkeleton />
        ) : (
          <>
            {/* Stat Cards */}
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardHeader className="pb-2">
                  <CardDescription className="flex items-center gap-1">
                    <Bell className="h-3 w-3" />
                    Total Notifications
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <span className="text-4xl font-bold">{notifications.length}</span>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardDescription className="flex items-center gap-1">
                    <XCircle className="h-3 w-3" />
                    Critical
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <span className={`text-4xl font-bold ${criticalCount > 0 ? "text-red-500" : "text-emerald-500"}`}>
                    {criticalCount}
                  </span>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardDescription className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3" />
                    Channels Active
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <span className="text-4xl font-bold">{enabledChannelsCount}</span>
                  <span className="text-sm text-muted-foreground ml-2">
                    of {channels.length}
                  </span>
                </CardContent>
              </Card>
            </div>

            {/* Channel Status */}
            <div className="space-y-2">
              <h2 className="text-xl font-semibold">Channel Status</h2>
              <div className="grid gap-4 md:grid-cols-3">
                {channels.map((channel) => (
                  <Card key={channel.id}>
                    <CardHeader className="pb-2">
                      <CardTitle className="flex items-center gap-2 text-base">
                        {channelIcon(channel.type)}
                        {channel.name}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="flex items-center gap-2">
                      {channel.enabled ? (
                        <Badge className="bg-emerald-600 hover:bg-emerald-700">Enabled</Badge>
                      ) : (
                        <Badge variant="outline" className="text-muted-foreground">Disabled</Badge>
                      )}
                      {channel.configured ? (
                        <Badge variant="outline" className="border-emerald-500 text-emerald-500">Configured</Badge>
                      ) : (
                        <Badge variant="outline" className="border-amber-500 text-amber-500">Not Configured</Badge>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>

            {/* Notification List */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold">Notification History</h2>
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
                        <TableHead>Time</TableHead>
                        <TableHead>Title</TableHead>
                        <TableHead>Severity</TableHead>
                        <TableHead>Channel</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="max-w-[400px]">Message</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredNotifications.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                            No notifications match the current filter
                          </TableCell>
                        </TableRow>
                      ) : (
                        filteredNotifications.map((notification) => (
                          <TableRow key={notification.id}>
                            <TableCell className="whitespace-nowrap text-sm">
                              {formatDateTime(notification.created_at)}
                            </TableCell>
                            <TableCell className="font-medium text-sm">
                              {notification.title}
                            </TableCell>
                            <TableCell>{severityBadge(notification.severity)}</TableCell>
                            <TableCell>
                              <Badge variant="outline">{notification.channel}</Badge>
                            </TableCell>
                            <TableCell>
                              {notification.success ? (
                                <div className="flex items-center gap-1 text-emerald-500">
                                  <CheckCircle className="h-4 w-4" />
                                  <span className="text-xs">Success</span>
                                </div>
                              ) : (
                                <div className="flex items-center gap-1 text-red-500">
                                  <XCircle className="h-4 w-4" />
                                  <span className="text-xs">Failed</span>
                                </div>
                              )}
                            </TableCell>
                            <TableCell className="max-w-[400px] text-sm">
                              {notification.message}
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
