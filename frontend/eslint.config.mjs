// ESLint flat config (required by ESLint 9 + eslint-config-next 16).
// Migrated from .eslintrc.json. Imports the next core-web-vitals
// preset directly — it ships a native flat-config array in v16,
// no FlatCompat shim needed.
import nextCoreWebVitals from "eslint-config-next/core-web-vitals"

const config = [
  ...nextCoreWebVitals,

  {
    // Standard ignores — don't lint generated or vendored files.
    ignores: [
      ".next/**",
      "node_modules/**",
      "out/**",
      "coverage/**",
      "next-env.d.ts",
    ],
  },
]

export default config
