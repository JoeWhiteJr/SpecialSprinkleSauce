import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import PipelinePage from "@/app/pipeline/page"

describe("Pipeline Page", () => {
  it("renders page title", () => {
    render(<PipelinePage />)
    expect(screen.getByRole("heading", { name: /Pipeline Runner/i })).toBeInTheDocument()
  })

  it("renders Run Pipeline button", () => {
    render(<PipelinePage />)
    expect(screen.getByText("Run Pipeline")).toBeInTheDocument()
  })

  it("renders ticker input", () => {
    render(<PipelinePage />)
    expect(screen.getByPlaceholderText(/NVDA/i)).toBeInTheDocument()
  })

  it("renders quick test ticker buttons", () => {
    render(<PipelinePage />)
    expect(screen.getByText("NVDA")).toBeInTheDocument()
    expect(screen.getByText("XOM")).toBeInTheDocument()
    expect(screen.getByText("TSM")).toBeInTheDocument()
  })
})
