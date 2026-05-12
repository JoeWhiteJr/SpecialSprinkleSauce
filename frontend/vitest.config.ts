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
      // Starting thresholds — INTENTIONALLY LOW. Ratchet upward as the
      // suite matures. Branches are deliberately lower (50%) than the
      // other metrics (60%) because every defensive `if`/early-return
      // adds two branch arms, and we want the gate to flag real gaps in
      // behavior coverage rather than guard-clause noise.
      thresholds: {
        lines: 60,
        functions: 60,
        statements: 60,
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
