import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import NotificationsPage from "@/app/notifications/page"

describe("Notifications Page", () => {
  it("renders page title", () => {
    render(<NotificationsPage />)
    expect(screen.getByRole("heading", { name: /Notifications/i })).toBeInTheDocument()
  })

  it("renders subtitle text", () => {
    render(<NotificationsPage />)
    expect(
      screen.getByText(/Monitor notification/i)
    ).toBeInTheDocument()
  })

  it("renders Send Test button", () => {
    render(<NotificationsPage />)
    expect(screen.getByText("Send Test")).toBeInTheDocument()
  })
})
