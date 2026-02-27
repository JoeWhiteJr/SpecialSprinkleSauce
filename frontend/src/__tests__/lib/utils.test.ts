import { describe, it, expect } from "vitest"
import { cn, formatCurrency, formatPercent, formatDate } from "@/lib/utils"

describe("cn", () => {
  it("merges class names", () => {
    expect(cn("foo", "bar")).toBe("foo bar")
  })
  it("handles conditional classes", () => {
    expect(cn("foo", false && "bar", "baz")).toBe("foo baz")
  })
})

describe("formatCurrency", () => {
  it("formats positive values", () => {
    expect(formatCurrency(1234.56)).toBe("$1,234.56")
  })
  it("formats negative values", () => {
    expect(formatCurrency(-500)).toBe("-$500.00")
  })
  it("formats zero", () => {
    expect(formatCurrency(0)).toBe("$0.00")
  })
})

describe("formatPercent", () => {
  it("formats positive with + sign", () => {
    expect(formatPercent(5.5)).toBe("+5.50%")
  })
  it("formats negative values", () => {
    expect(formatPercent(-3.2)).toBe("-3.20%")
  })
  it("formats zero with + sign", () => {
    expect(formatPercent(0)).toBe("+0.00%")
  })
})

describe("formatDate", () => {
  it("formats ISO date string", () => {
    const result = formatDate("2024-06-15T12:00:00Z")
    expect(result).toContain("Jun")
    expect(result).toContain("15")
    expect(result).toContain("2024")
  })
})
