import { Card, CardHeader, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export function StatCardSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className={`grid gap-4 md:grid-cols-${count}`}>
      {Array.from({ length: count }, (_, i) => (
        <Card key={i}>
          <CardHeader>
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-10 w-16" />
          </CardHeader>
        </Card>
      ))}
    </div>
  )
}

export function TableSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <Card>
      <CardContent className="py-6 space-y-3">
        {Array.from({ length: rows }, (_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </CardContent>
    </Card>
  )
}

export function PageSkeleton({ statCards = 3, tableRows = 4 }: { statCards?: number; tableRows?: number }) {
  return (
    <div className="space-y-6">
      <StatCardSkeleton count={statCards} />
      <TableSkeleton rows={tableRows} />
    </div>
  )
}
