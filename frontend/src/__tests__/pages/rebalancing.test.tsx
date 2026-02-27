import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import RebalancingPage from "@/app/rebalancing/page"

describe("Rebalancing Page", () => {
  it("renders page title", () => {
    render(<RebalancingPage />)
    expect(screen.getByText("Portfolio Rebalancing")).toBeInTheDocument()
  })

  it("renders drift table column Target%", () => {
    render(<RebalancingPage />)
    expect(screen.getByText("Target %")).toBeInTheDocument()
  })

  it("renders Save Targets button", () => {
    render(<RebalancingPage />)
    expect(screen.getByText("Save Targets")).toBeInTheDocument()
  })
})
