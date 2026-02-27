import { Badge } from "@/components/ui/badge"

export function severityBadge(severity: "info" | "warning" | "critical") {
  switch (severity) {
    case "info":
      return <Badge variant="outline" className="border-blue-500 text-blue-500">Info</Badge>
    case "warning":
      return <Badge className="bg-amber-600 hover:bg-amber-700">Warning</Badge>
    case "critical":
      return <Badge variant="destructive">Critical</Badge>
  }
}

export function actionBadge(action: "BUY" | "SELL" | "HOLD" | "BLOCKED") {
  switch (action) {
    case "BUY":
      return <Badge className="bg-emerald-600 hover:bg-emerald-700">BUY</Badge>
    case "SELL":
      return <Badge variant="destructive">SELL</Badge>
    case "HOLD":
      return <Badge className="bg-amber-600 hover:bg-amber-700">HOLD</Badge>
    case "BLOCKED":
      return <Badge variant="outline">BLOCKED</Badge>
  }
}

export function statusBadge(status: string) {
  switch (status) {
    case "active":
    case "approved":
    case "completed":
      return <Badge className="bg-emerald-600 hover:bg-emerald-700">{status}</Badge>
    case "warning":
    case "pending":
      return <Badge className="bg-amber-600 hover:bg-amber-700">{status}</Badge>
    case "halted":
    case "rejected":
      return <Badge variant="destructive">{status}</Badge>
    default:
      return <Badge variant="outline">{status}</Badge>
  }
}
