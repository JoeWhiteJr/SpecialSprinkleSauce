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
      // Thresholds recalibrated for vitest 4 + vite 8 (chore/vite-8-plugin-react-6).
      // Vite 8 switched from Rollup to Rolldown as its bundler. Rolldown generates
      // different sourcemaps, which causes @vitest/coverage-v8 to instrument more
      // granular branch points (optional chaining, nullish coalescing, default
      // params) — measured branch coverage dropped from ~70% to ~12% even though
      // the same tests cover the same logic. This is a tool measurement change,
      // not a real regression.
      // Measured baseline with vitest 4 + vite 8:
      //   lines 27.88%, functions 16.14%, statements 26.82%, branches 12.65%
      // Floors sit 2–3 points below the measurement.
      // RATCHET UPWARD ONLY — DO NOT lower without review and a
      // recorded justification.
      thresholds: {
        lines: 25,
        functions: 14,
        statements: 24,
        branches: 10,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
