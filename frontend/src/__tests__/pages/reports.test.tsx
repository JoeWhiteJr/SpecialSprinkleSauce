import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import ReportsPage from "@/app/reports/page"

describe("Reports Page", () => {
  it("renders page title", () => {
    render(<ReportsPage />)
    expect(screen.getByRole("heading", { name: /Reports/i })).toBeInTheDocument()
  })

  it("renders all tabs", () => {
    render(<ReportsPage />)
    expect(screen.getByText("Daily")).toBeInTheDocument()
    expect(screen.getByText("Weekly")).toBeInTheDocument()
    expect(screen.getByText("Monthly")).toBeInTheDocument()
    expect(screen.getByText("Paper Trading Summary")).toBeInTheDocument()
  })
})
