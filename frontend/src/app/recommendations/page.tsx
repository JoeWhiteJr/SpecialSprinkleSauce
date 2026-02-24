"use client"

import { useState } from "react"
import { DashboardShell } from "@/components/dashboard-shell"
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { useRecommendations } from "@/hooks/use-api"
import { mockRecommendations } from "@/lib/mock-data"
import { formatDateTime, cn } from "@/lib/utils"
import type { TradeRecommendation } from "@/lib/types"
import {
  TrendingUp,
  TrendingDown,
  Check,
  X,
  Clock,
  User,
} from "lucide-react"

function CardSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-8 w-20" />
        <Skeleton className="h-4 w-32" />
      </CardHeader>
      <CardContent className="space-y-3">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-3/4" />
        <Skeleton className="h-6 w-full rounded-full" />
        <Skeleton className="h-3 w-1/2" />
      </CardContent>
    </Card>
  )
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">Confidence</span>
        <span className="font-medium">{pct}%</span>
      </div>
      <div className="h-2 w-full rounded-full bg-muted">
        <div
          className={cn(
            "h-2 rounded-full transition-all",
            pct >= 75
              ? "bg-emerald-500"
              : pct >= 50
                ? "bg-amber-500"
                : "bg-red-500"
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

function WasdenVerdictBadge({ verdict }: { verdict: string }) {
  const variant =
    verdict === "APPROVE"
      ? "success"
      : verdict === "VETO"
        ? "destructive"
        : "warning"
  return <Badge variant={variant}>{verdict}</Badge>
}

function RecommendationCard({ rec }: { rec: TradeRecommendation }) {
  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-2xl font-bold">{rec.ticker}</CardTitle>
          <Badge
            variant={rec.direction === "BUY" ? "success" : "destructive"}
            className="text-sm"
          >
            {rec.direction === "BUY" ? (
              <TrendingUp className="mr-1 h-3 w-3" />
            ) : (
              <TrendingDown className="mr-1 h-3 w-3" />
            )}
            {rec.direction}
          </Badge>
        </div>
        <CardDescription className="flex items-center gap-1 text-xs">
          <Clock className="h-3 w-3" />
          {formatDateTime(rec.created_at)}
        </CardDescription>
      </CardHeader>

      <CardContent className="flex-1 space-y-4">
        <ConfidenceBar value={rec.confidence} />

        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Quant Composite</span>
          <span className="font-mono font-medium">
            {(rec.quant_composite * 100).toFixed(0)}%
          </span>
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Wasden Verdict</span>
          <WasdenVerdictBadge verdict={rec.wasden_verdict} />
        </div>

        <Separator />

        <p className="text-sm text-muted-foreground leading-relaxed">
          {rec.reasoning}
        </p>
      </CardContent>

      <CardFooter className="pt-4">
        {rec.status === "pending" ? (
          <div className="flex w-full gap-2">
            <Button className="flex-1" variant="default" size="sm">
              <Check className="mr-1 h-4 w-4" />
              Approve
            </Button>
            <Button className="flex-1" variant="destructive" size="sm">
              <X className="mr-1 h-4 w-4" />
              Reject
            </Button>
          </div>
        ) : (
          <div className="w-full space-y-2">
            <div className="flex items-center justify-between">
              <Badge
                variant={rec.status === "approved" ? "success" : "destructive"}
              >
                {rec.status.toUpperCase()}
              </Badge>
              {rec.reviewed_at && (
                <span className="text-xs text-muted-foreground">
                  {formatDateTime(rec.reviewed_at)}
                </span>
              )}
            </div>
            {rec.reviewed_by && (
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <User className="h-3 w-3" />
                Reviewed by {rec.reviewed_by}
              </div>
            )}
            {rec.review_note && (
              <p className="text-xs text-muted-foreground italic">
                &ldquo;{rec.review_note}&rdquo;
              </p>
            )}
          </div>
        )}
      </CardFooter>
    </Card>
  )
}

export default function RecommendationsPage() {
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const { data: apiRecs, isLoading } = useRecommendations()

  const recommendations = apiRecs ?? mockRecommendations

  const filtered =
    statusFilter === "all"
      ? recommendations
      : recommendations.filter((r) => r.status === statusFilter)

  const counts = {
    all: recommendations.length,
    pending: recommendations.filter((r) => r.status === "pending").length,
    approved: recommendations.filter((r) => r.status === "approved").length,
    rejected: recommendations.filter((r) => r.status === "rejected").length,
  }

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Recommendations</h1>
            <p className="text-muted-foreground">
              Daily trade recommendations from the pipeline
            </p>
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All ({counts.all})</SelectItem>
              <SelectItem value="pending">Pending ({counts.pending})</SelectItem>
              <SelectItem value="approved">Approved ({counts.approved})</SelectItem>
              <SelectItem value="rejected">Rejected ({counts.rejected})</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {isLoading ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <CardSkeleton key={i} />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              No recommendations match the selected filter.
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filtered.map((rec) => (
              <RecommendationCard key={rec.id} rec={rec} />
            ))}
          </div>
        )}
      </div>
    </DashboardShell>
  )
}
