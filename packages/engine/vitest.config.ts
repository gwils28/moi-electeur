import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["test/**/*.test.ts"],
    coverage: {
      provider: "v8",
      include: ["src/**/*.ts"],
      // Seuil bloquant (SPEC § 12). Le squelette M0 ne contient pas de logique.
      thresholds: { lines: 90, functions: 90, branches: 90, statements: 90 },
    },
  },
});
