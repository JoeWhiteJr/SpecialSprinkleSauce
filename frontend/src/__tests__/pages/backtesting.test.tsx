import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import BacktestingPage from "@/app/backtesting/page"

describe("Backtesting Page", () => {
  it("renders page title", () => {
    render(<BacktestingPage />)
    expect(screen.getByRole("heading", { name: /Backtesting/i })).toBeInTheDocument()
  })

  it("renders Run Backtest button", () => {
    render(<BacktestingPage />)
    expect(screen.getByText("Run Backtest")).toBeInTheDocument()
  })

  it("renders results table header Ticker", () => {
    render(<BacktestingPage />)
    const headers = screen.getAllByText("Ticker")
    expect(headers.length).toBeGreaterThanOrEqual(1)
  })
})
