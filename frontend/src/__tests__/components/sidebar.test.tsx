import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { Sidebar } from "@/components/sidebar"

describe("Sidebar", () => {
  it("renders all navigation groups", () => {
    render(<Sidebar />)
    expect(screen.getByText("Trading")).toBeInTheDocument()
    expect(screen.getByText("Analysis")).toBeInTheDocument()
    expect(screen.getByText("Monitoring")).toBeInTheDocument()
    expect(screen.getByText("System")).toBeInTheDocument()
  })

  it("renders new navigation links", () => {
    render(<Sidebar />)
    expect(screen.getByText("Backtesting")).toBeInTheDocument()
    expect(screen.getByText("Rebalancing")).toBeInTheDocument()
    expect(screen.getByText("Reports")).toBeInTheDocument()
    expect(screen.getByText("Notifications")).toBeInTheDocument()
    expect(screen.getByText("Emergency")).toBeInTheDocument()
  })

  it("renders Wasden Watch branding", () => {
    render(<Sidebar />)
    expect(screen.getByText("Wasden Watch")).toBeInTheDocument()
    expect(screen.getByText("WW")).toBeInTheDocument()
  })
})
