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
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useDebates } from "@/hooks/use-api"
import { mockDebates } from "@/lib/mock-data"
import { formatDate, formatDateTime, cn } from "@/lib/utils"
import type { DebateTranscript, DebateRound } from "@/lib/types"
import {
  MessageSquare,
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Swords,
} from "lucide-react"

function CardSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-4 w-40" />
      </CardHeader>
      <CardContent className="space-y-2">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-4 w-20" />
      </CardContent>
    </Card>
  )
}

function ConfidenceIndicator({ value, color }: { value: number; color: string }) {
  const pct = Math.round(value * 100)
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 flex-1 rounded-full bg-muted">
        <div
          className={cn("h-1.5 rounded-full", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-mono font-medium w-8 text-right">{pct}%</span>
    </div>
  )
}

function RoundPanel({
  round,
  side,
}: {
  round: DebateRound
  side: "bull" | "bear"
}) {
  const isBull = side === "bull"
  return (
    <div
      className={cn(
        "rounded-lg border p-4 space-y-3",
        isBull
          ? "border-emerald-500/20 bg-emerald-500/5"
          : "border-red-500/20 bg-red-500/5"
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isBull ? (
            <TrendingUp className="h-4 w-4 text-emerald-500" />
          ) : (
            <TrendingDown className="h-4 w-4 text-red-500" />
          )}
          <span
            className={cn(
              "text-xs font-semibold uppercase tracking-wide",
              isBull ? "text-emerald-500" : "text-red-500"
            )}
          >
            {isBull ? "Bull Case (Claude)" : "Bear Case (Gemini)"}
          </span>
        </div>
        <Badge variant="outline" className="text-[10px]">
          Round {round.round_number}
        </Badge>
      </div>
      <p className="text-sm text-muted-foreground leading-relaxed">
        {isBull ? round.bull_argument : round.bear_argument}
      </p>
      <ConfidenceIndicator
        value={isBull ? round.bull_confidence : round.bear_confidence}
        color={isBull ? "bg-emerald-500" : "bg-red-500"}
      />
    </div>
  )
}

function DebateListView({
  debates,
  onSelect,
  isLoading,
}: {
  debates: DebateTranscript[]
  onSelect: (debate: DebateTranscript) => void
  isLoading: boolean
}) {
  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <CardSkeleton key={i} />
        ))}
      </div>
    )
  }

  if (debates.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          No debate transcripts available.
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {debates.map((debate) => (
        <Card
          key={debate.id}
          className="cursor-pointer transition-colors hover:bg-muted/50"
          onClick={() => onSelect(debate)}
        >
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-xl font-bold">{debate.ticker}</CardTitle>
              <Badge
                variant={
                  debate.outcome === "agreement" ? "success" : "warning"
                }
              >
                {debate.outcome.toUpperCase()}
              </Badge>
            </div>
            <CardDescription>{formatDate(debate.created_at)}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <div className="flex items-center gap-1">
                <MessageSquare className="h-4 w-4" />
                {debate.rounds.length} rounds
              </div>
              <div className="flex items-center gap-1">
                <Swords className="h-4 w-4" />
                {debate.rounds.length > 0
                  ? `Bull ${Math.round(debate.rounds[debate.rounds.length - 1].bull_confidence * 100)}% / Bear ${Math.round(debate.rounds[debate.rounds.length - 1].bear_confidence * 100)}%`
                  : "No rounds"}
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function DebateDetailView({
  debate,
  onBack,
}: {
  debate: DebateTranscript
  onBack: () => void
}) {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={onBack}>
          <ArrowLeft className="mr-1 h-4 w-4" />
          Back to Debates
        </Button>
        <Separator orientation="vertical" className="h-6" />
        <h2 className="text-xl font-bold">{debate.ticker}</h2>
        <Badge
          variant={debate.outcome === "agreement" ? "success" : "warning"}
        >
          {debate.outcome.toUpperCase()}
        </Badge>
        <span className="text-sm text-muted-foreground">
          {formatDateTime(debate.created_at)}
        </span>
      </div>

      <ScrollArea className="h-[calc(100vh-250px)]">
        <div className="space-y-8">
          {debate.rounds.map((round) => (
            <div key={round.round_number} className="space-y-4">
              <div className="flex items-center gap-2">
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">
                  {round.round_number}
                </div>
                <span className="text-sm font-medium text-muted-foreground">
                  Round {round.round_number}
                </span>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <RoundPanel round={round} side="bull" />
                <RoundPanel round={round} side="bear" />
              </div>
            </div>
          ))}

          {/* Final Outcome */}
          <Separator />
          <div className="flex items-center justify-center gap-3 py-4">
            <span className="text-sm font-medium text-muted-foreground">
              Final Outcome:
            </span>
            <Badge
              variant={debate.outcome === "agreement" ? "success" : "warning"}
              className="text-sm"
            >
              {debate.outcome === "agreement"
                ? "AGREEMENT REACHED"
                : "DISAGREEMENT — ESCALATED TO JURY"}
            </Badge>
          </div>
        </div>
      </ScrollArea>
    </div>
  )
}

export default function DebatesPage() {
  const [selectedDebate, setSelectedDebate] = useState<DebateTranscript | null>(
    null
  )
  const { data: apiDebates, isLoading } = useDebates()
  const debates = apiDebates ?? mockDebates

  return (
    <DashboardShell>
      <div className="space-y-6">
        {selectedDebate ? (
          <DebateDetailView
            debate={selectedDebate}
            onBack={() => setSelectedDebate(null)}
          />
        ) : (
          <>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Debates</h1>
              <p className="text-muted-foreground">
                Bull vs Bear debate transcripts from the pipeline
              </p>
            </div>
            <DebateListView
              debates={debates}
              onSelect={setSelectedDebate}
              isLoading={isLoading}
            />
          </>
        )}
      </div>
    </DashboardShell>
  )
}
