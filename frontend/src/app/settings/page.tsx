"use client"

import { useState } from "react"
import { DashboardShell } from "@/components/dashboard-shell"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert"
import {
  Settings,
  AlertTriangle,
  Database,
  Cpu,
  Wifi,
  WifiOff,
  Shield,
  Clock,
  ToggleLeft,
} from "lucide-react"
import { useSettings } from "@/hooks/use-api"
import { mockSettings } from "@/lib/mock-data"
import { formatDate } from "@/lib/utils"
import type { SystemSetting } from "@/lib/types"

interface ApiStatusEntry {
  connected: boolean
  latency_ms: number
}

const API_SERVICES = [
  { key: "supabase", label: "Supabase", icon: Database, description: "PostgreSQL database" },
  { key: "claude", label: "Claude API", icon: Cpu, description: "Anthropic Claude for Wasden Watch" },
  { key: "gemini", label: "Gemini API", icon: Cpu, description: "Google Gemini for debate agents" },
  { key: "alpaca", label: "Alpaca API", icon: Cpu, description: "Brokerage execution" },
]

const RISK_CONSTANTS = [
  { key: "MAX_POSITION_PCT", label: "Max Position Size", description: "Maximum single position as percentage of portfolio", format: (v: string) => `${(parseFloat(v) * 100).toFixed(0)}%` },
  { key: "RISK_PER_TRADE_PCT", label: "Risk Per Trade", description: "Maximum risk exposure per individual trade", format: (v: string) => `${(parseFloat(v) * 100).toFixed(1)}%` },
  { key: "MIN_CASH_RESERVE_PCT", label: "Min Cash Reserve", description: "Minimum cash reserve maintained at all times", format: (v: string) => `${(parseFloat(v) * 100).toFixed(0)}%` },
  { key: "MAX_CORRELATED_POSITIONS", label: "Max Correlated Positions", description: "Maximum number of correlated positions allowed simultaneously", format: (v: string) => v },
  { key: "CORRELATION_THRESHOLD", label: "Correlation Threshold", description: "Pearson correlation threshold for position grouping", format: (v: string) => v },
]

const mockApiStatus: Record<string, ApiStatusEntry> = {
  supabase: { connected: true, latency_ms: 12 },
  claude: { connected: true, latency_ms: 245 },
  gemini: { connected: true, latency_ms: 189 },
  alpaca: { connected: false, latency_ms: 0 },
}

function getSettingValue(settings: SystemSetting[], key: string): string | undefined {
  return settings.find((s) => s.key === key)?.value
}

function getSettingMeta(settings: SystemSetting[], key: string): SystemSetting | undefined {
  return settings.find((s) => s.key === key)
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-72" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-10 w-full" />
        </CardContent>
      </Card>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-6 w-20" />
            </CardHeader>
          </Card>
        ))}
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-8 w-16" />
            </CardHeader>
          </Card>
        ))}
      </div>
    </div>
  )
}

export default function SettingsPage() {
  const { data: apiData, isLoading } = useSettings()

  const settings = apiData?.settings ?? mockSettings
  const apiStatus = apiData?.api_status ?? mockApiStatus

  const tradingMode = getSettingValue(settings, "TRADING_MODE") ?? "paper"
  const useMockData = getSettingValue(settings, "USE_MOCK_DATA") ?? "true"

  const [localTradingMode, setLocalTradingMode] = useState<string | null>(null)
  const [localMockData, setLocalMockData] = useState<string | null>(null)

  const effectiveTradingMode = localTradingMode ?? tradingMode
  const effectiveMockData = localMockData ?? useMockData

  const isLive = effectiveTradingMode === "live"
  const isMockEnabled = effectiveMockData === "true"

  const handleTradingModeToggle = (checked: boolean) => {
    const newMode = checked ? "live" : "paper"
    setLocalTradingMode(newMode)
    // In production, this would call updateSetting API
  }

  const handleMockDataToggle = (checked: boolean) => {
    const newValue = checked ? "true" : "false"
    setLocalMockData(newValue)
    // In production, this would call updateSetting API
  }

  return (
    <DashboardShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Settings className="h-8 w-8" />
            Settings & Configuration
          </h1>
          <p className="text-muted-foreground mt-1">
            System configuration, API status, and risk constants.
          </p>
        </div>

        {isLoading ? (
          <LoadingSkeleton />
        ) : (
          <>
            {/* Trading Mode Toggle */}
            <Card className={isLive ? "border-red-500/50" : "border-blue-500/50"}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <ToggleLeft className="h-5 w-5" />
                      Trading Mode
                    </CardTitle>
                    <CardDescription className="mt-1">
                      Controls whether the system executes real trades or simulates them
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-3">
                    {isLive ? (
                      <Badge variant="destructive" className="text-sm px-3 py-1">LIVE</Badge>
                    ) : (
                      <Badge className="bg-blue-600 hover:bg-blue-700 text-sm px-3 py-1">PAPER</Badge>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Label htmlFor="trading-mode" className="text-sm">
                      Paper Trading
                    </Label>
                    <Switch
                      id="trading-mode"
                      checked={isLive}
                      onCheckedChange={handleTradingModeToggle}
                    />
                    <Label htmlFor="trading-mode" className="text-sm">
                      Live Trading
                    </Label>
                  </div>
                </div>
                {isLive && (
                  <Alert variant="destructive" className="mt-4">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertTitle>Live Trading Active</AlertTitle>
                    <AlertDescription>
                      The system will execute real trades through the Alpaca brokerage API. All orders
                      will use real capital. Ensure risk parameters are properly configured before proceeding.
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>

            {/* API Status Grid */}
            <div>
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <Wifi className="h-5 w-5" />
                API Status
              </h2>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {API_SERVICES.map((service) => {
                  const status = (apiStatus as Record<string, ApiStatusEntry>)[service.key]
                  const connected = status?.connected ?? false
                  const latency = status?.latency_ms ?? 0

                  return (
                    <Card key={service.key}>
                      <CardHeader className="pb-2">
                        <div className="flex items-center justify-between">
                          <CardDescription className="flex items-center gap-1">
                            <service.icon className="h-3 w-3" />
                            {service.label}
                          </CardDescription>
                          {connected ? (
                            <Badge className="bg-emerald-600 hover:bg-emerald-700">Connected</Badge>
                          ) : (
                            <Badge variant="destructive">Disconnected</Badge>
                          )}
                        </div>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm text-muted-foreground">{service.description}</p>
                        {connected ? (
                          <div className="flex items-center gap-1 mt-2 text-sm">
                            <Clock className="h-3 w-3 text-muted-foreground" />
                            <span className="text-muted-foreground">Latency:</span>
                            <span
                              className={`font-medium ${
                                latency < 100
                                  ? "text-emerald-500"
                                  : latency < 300
                                  ? "text-amber-500"
                                  : "text-red-500"
                              }`}
                            >
                              {latency}ms
                            </span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1 mt-2 text-sm text-red-400">
                            <WifiOff className="h-3 w-3" />
                            <span>Service unavailable</span>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            </div>

            <Separator />

            {/* Risk Constants */}
            <div>
              <h2 className="text-xl font-semibold mb-2 flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Risk Constants
              </h2>
              <Alert className="mb-4">
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>Read Only</AlertTitle>
                <AlertDescription>
                  Changes to risk constants require human approval and cannot be modified through the dashboard.
                </AlertDescription>
              </Alert>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {RISK_CONSTANTS.map((constant) => {
                  const setting = getSettingMeta(settings, constant.key)
                  const rawValue = setting?.value ?? "N/A"
                  const displayValue = setting ? constant.format(setting.value) : "N/A"

                  return (
                    <Card key={constant.key}>
                      <CardHeader className="pb-2">
                        <CardDescription>{constant.label}</CardDescription>
                        <CardTitle className="text-2xl">{displayValue}</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm text-muted-foreground">{constant.description}</p>
                        {setting && (
                          <p className="text-xs text-muted-foreground mt-2">
                            Last updated: {formatDate(setting.updated_at)}
                          </p>
                        )}
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            </div>

            <Separator />

            {/* System Info */}
            <div>
              <h2 className="text-xl font-semibold mb-4">System Info</h2>
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Database className="h-4 w-4" />
                      Mock Data Mode
                    </CardTitle>
                    <CardDescription>
                      When enabled, the system uses local mock data instead of Supabase
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-3">
                      <Switch
                        id="mock-data"
                        checked={isMockEnabled}
                        onCheckedChange={handleMockDataToggle}
                      />
                      <Label htmlFor="mock-data" className="text-sm">
                        {isMockEnabled ? "Mock data enabled" : "Using live data"}
                      </Label>
                      <Badge variant="outline" className={isMockEnabled ? "border-amber-500 text-amber-500" : "border-emerald-500 text-emerald-500"}>
                        {isMockEnabled ? "MOCK" : "LIVE"}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Clock className="h-4 w-4" />
                      Configuration Timestamps
                    </CardTitle>
                    <CardDescription>
                      Last modified dates for system settings
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {settings.slice(0, 4).map((setting) => (
                        <div key={setting.key} className="flex items-center justify-between text-sm">
                          <span className="font-mono text-muted-foreground">{setting.key}</span>
                          <span className="text-muted-foreground">
                            {formatDate(setting.updated_at)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </>
        )}
      </div>
    </DashboardShell>
  )
}
