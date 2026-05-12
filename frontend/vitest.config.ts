import { defineConfig } from "vitest/config"
import react from "@vitejs/plugin-react"
import path from "path"

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    globals: true,
    coverage: {
      // v8 is faster than istanbul and ships in the Node runtime.
      // Requires `@vitest/coverage-v8` to be installed (CI installs it
      // on the fly today — see ci.yml "Install coverage provider" step;
      // follow-up to move into devDependencies).
      provider: "v8",
      reporter: ["text", "html", "json-summary", "lcov"],
      reportsDirectory: "./coverage",
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.d.ts",
        "src/**/*.stories.{ts,tsx}",
        "src/**/__tests__/**",
        "src/**/*.test.{ts,tsx}",
        "src/**/*.spec.{ts,tsx}",
      ],
      // Starting thresholds — calibrated to measured baseline on main
      // (lines 30.6%, functions 25%, statements 30.6%, branches 70.6%).
      // Each floor sits ~2–3 points below the measurement so trivial
      // fluctuations don't break CI, but a real regression does.
      // Branches start higher because defensive `if`/early-return code
      // already over-covers branches relative to lines.
      // RATCHET UPWARD ONLY — DO NOT lower without review and a
      // recorded justification.
      thresholds: {
        lines: 28,
        functions: 22,
        statements: 28,
        branches: 50,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
