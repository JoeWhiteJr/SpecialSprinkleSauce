"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import {
  BarChart3,
  Lightbulb,
  BookOpen,
  MessageSquare,
  Users,
  ShieldAlert,
  AlertTriangle,
  Eye,
  Filter,
  Settings,
} from "lucide-react"
import { ScrollArea } from "@/components/ui/scroll-area"

const navGroups = [
  {
    label: "Trading",
    items: [
      { href: "/portfolio", label: "Portfolio", icon: BarChart3 },
      { href: "/recommendations", label: "Recommendations", icon: Lightbulb },
    ],
  },
  {
    label: "Analysis",
    items: [
      { href: "/journal", label: "Decision Journal", icon: BookOpen },
      { href: "/debates", label: "Debates", icon: MessageSquare },
      { href: "/jury", label: "Jury Votes", icon: Users },
    ],
  },
  {
    label: "Monitoring",
    items: [
      { href: "/overrides", label: "Overrides", icon: ShieldAlert },
      { href: "/alerts", label: "Alerts", icon: AlertTriangle },
      { href: "/bias", label: "Bias Monitor", icon: Eye },
      { href: "/screening", label: "Screening", icon: Filter },
    ],
  },
  {
    label: "System",
    items: [
      { href: "/settings", label: "Settings", icon: Settings },
    ],
  },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <div className="flex h-full w-64 flex-col border-r bg-card">
      <div className="flex h-16 items-center border-b px-6">
        <Link href="/portfolio" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold text-sm">
            WW
          </div>
          <span className="font-semibold text-lg">Wasden Watch</span>
        </Link>
      </div>
      <ScrollArea className="flex-1 px-3 py-4">
        <nav className="space-y-6">
          {navGroups.map((group) => (
            <div key={group.label}>
              <h4 className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {group.label}
              </h4>
              <div className="space-y-1">
                {group.items.map((item) => {
                  const isActive = pathname === item.href
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={cn(
                        "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                        isActive
                          ? "bg-primary/10 text-primary"
                          : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                      )}
                    >
                      <item.icon className="h-4 w-4" />
                      {item.label}
                    </Link>
                  )
                })}
              </div>
            </div>
          ))}
        </nav>
      </ScrollArea>
    </div>
  )
}
