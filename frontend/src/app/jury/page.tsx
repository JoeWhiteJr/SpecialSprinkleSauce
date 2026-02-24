"use client"

import { DashboardShell } from "@/components/dashboard-shell"
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert"
import { useJuryVotes, useJuryStats } from "@/hooks/use-api"
import { mockJuryVotes, mockJuryStats } from "@/lib/mock-data"
import { formatPercent, cn } from "@/lib/utils"
import type { JuryVote, JuryStats } from "@/lib/types"
import {
  Users,
  Scale,
  AlertTriangle,
  ShieldCheck,
  TrendingUp,
  TrendingDown,
  Minus,
} from "lucide-react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts"

function StatCardSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-4 rounded" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-20 mb-1" />
        <Skeleton className="h-3 w-16" />
      </CardContent>
    </Card>
  )
}

function VoteCardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <Skeleton className="h-4 w-32" />
      </CardHeader>
      <CardContent className="space-y-2">
        <Skeleton className="h-6 w-16" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-3/4" />
      </CardContent>
    </Card>
  )
}

function VoteBadge({ vote }: { vote: string }) {
  const config = {
    BUY: { variant: "success" as const, icon: TrendingUp },
    SELL: { variant: "destructive" as const, icon: TrendingDown },
    HOLD: { variant: "warning" as const, icon: Minus },
  }
  const { variant, icon: Icon } = config[vote as keyof typeof config] ?? {
    variant: "secondary" as const,
    icon: Minus,
  }

  return (
    <Badge variant={variant} className="text-sm">
      <Icon className="mr-1 h-3 w-3" />
      {vote}
    </Badge>
  )
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">Confidence</span>
        <span className="font-mono font-medium">{pct}%</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-muted">
        <div
          className={cn(
            "h-1.5 rounded-full",
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

function AgentVoteCard({ vote }: { vote: JuryVote }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">
            Agent {vote.agent_id}
          </CardTitle>
          <VoteBadge vote={vote.vote} />
        </div>
        <CardDescription className="text-xs">
          {vote.agent_perspective}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <ConfidenceBar value={vote.confidence} />
        <p className="text-xs text-muted-foreground leading-relaxed line-clamp-3">
          {vote.reasoning}
        </p>
      </CardContent>
    </Card>
  )
}

function VoteSummaryChart({ votes }: { votes: JuryVote[] }) {
  const buys = votes.filter((v) => v.vote === "BUY").length
  const sells = votes.filter((v) => v.vote === "SELL").length
  const holds = votes.filter((v) => v.vote === "HOLD").length

  const data = [
    { name: "BUY", count: buys, color: "#10b981" },
    { name: "SELL", count: sells, color: "#ef4444" },
    { name: "HOLD", count: holds, color: "#f59e0b" },
  ]

  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis dataKey="name" tick={{ fontSize: 12 }} />
        <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
        <Tooltip
          contentStyle={{
            backgroundColor: "hsl(var(--card))",
            border: "1px solid hsl(var(--border))",
            borderRadius: "8px",
          }}
          labelStyle={{ color: "hsl(var(--foreground))" }}
        />
        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
          {data.map((entry, index) => (
            <Cell key={index} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

export default function JuryPage() {
  const { data: apiVotes, isLoading: votesLoading } = useJuryVotes("")
  const { data: apiStats, isLoading: statsLoading } = useJuryStats()

  const votes = apiVotes ?? mockJuryVotes
  const stats = apiStats ?? mockJuryStats

  const buys = votes.filter((v) => v.vote === "BUY").length
  const sells = votes.filter((v) => v.vote === "SELL").length
  const holds = votes.filter((v) => v.vote === "HOLD").length
  const total = votes.length
  const isTied = buys === sells && buys === 5

  const statCards = [
    {
      title: "Total Sessions",
      value: stats.total_sessions,
      description: `${stats.total_votes} total votes cast`,
      icon: Users,
    },
    {
      title: "Agreement Rate",
      value: `${(stats.agreement_rate * 100).toFixed(0)}%`,
      description: "Across all jury sessions",
      icon: ShieldCheck,
    },
    {
      title: "Escalations",
      value: stats.escalation_count,
      description: "Escalated to human review",
      icon: AlertTriangle,
    },
  ]

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Jury Votes</h1>
          <p className="text-muted-foreground">
            10-agent jury vote breakdown and consensus analysis
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid gap-4 md:grid-cols-3">
          {statsLoading
            ? Array.from({ length: 3 }).map((_, i) => (
                <StatCardSkeleton key={i} />
              ))
            : statCards.map((card) => (
                <Card key={card.title}>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      {card.title}
                    </CardTitle>
                    <card.icon className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{card.value}</div>
                    <p className="text-xs text-muted-foreground">
                      {card.description}
                    </p>
                  </CardContent>
                </Card>
              ))}
        </div>

        {/* Escalation Warning */}
        {isTied && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>5-5 Jury Tie Detected</AlertTitle>
            <AlertDescription>
              This jury vote resulted in a 5-5 tie between BUY and SELL. Per
              system rules, this decision has been escalated to human review.
              Ties are never auto-resolved.
            </AlertDescription>
          </Alert>
        )}

        {stats.escalation_count > 0 && !isTied && (
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Escalation History</AlertTitle>
            <AlertDescription>
              {stats.escalation_count} jury session(s) have been escalated to
              human review due to close votes or high-stakes decisions.
            </AlertDescription>
          </Alert>
        )}

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Vote Summary Chart */}
          <Card className="lg:col-span-1">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Scale className="h-4 w-4" />
                Vote Summary
              </CardTitle>
              <CardDescription>
                Distribution across {total} agent votes
              </CardDescription>
            </CardHeader>
            <CardContent>
              {votesLoading ? (
                <Skeleton className="h-[250px] w-full" />
              ) : (
                <>
                  <VoteSummaryChart votes={votes} />
                  <Separator className="my-4" />
                  <div className="flex items-center justify-center gap-4 text-sm">
                    <div className="flex items-center gap-1">
                      <div className="h-3 w-3 rounded-full bg-emerald-500" />
                      <span>BUY: {buys}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="h-3 w-3 rounded-full bg-red-500" />
                      <span>SELL: {sells}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="h-3 w-3 rounded-full bg-amber-500" />
                      <span>HOLD: {holds}</span>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Agent Vote Grid */}
          <div className="lg:col-span-2">
            <div className="grid gap-4 sm:grid-cols-2">
              {votesLoading
                ? Array.from({ length: 10 }).map((_, i) => (
                    <VoteCardSkeleton key={i} />
                  ))
                : votes.map((vote) => (
                    <AgentVoteCard key={vote.agent_id} vote={vote} />
                  ))}
            </div>
          </div>
        </div>
      </div>
    </DashboardShell>
  )
}
