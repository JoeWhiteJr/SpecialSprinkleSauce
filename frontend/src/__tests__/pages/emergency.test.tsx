import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import EmergencyPage from "@/app/emergency/page"

describe("Emergency Page", () => {
  it("renders page title", () => {
    render(<EmergencyPage />)
    expect(screen.getByText("Emergency Controls")).toBeInTheDocument()
  })

  it("renders TRADING ACTIVE status banner", () => {
    render(<EmergencyPage />)
    expect(screen.getByText("TRADING ACTIVE")).toBeInTheDocument()
  })

  it("renders Emergency Shutdown action card text", () => {
    render(<EmergencyPage />)
    expect(screen.getByText("Emergency Shutdown")).toBeInTheDocument()
  })
})
