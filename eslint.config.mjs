// Configuration ESLint racine (flat config).
import js from "@eslint/js";
import tseslint from "typescript-eslint";

// Le moteur de calcul ne doit faire aucune I/O (CLAUDE.md, PLAN § 1).
const ENGINE_FORBIDDEN_GLOBALS = [
  "fetch",
  "XMLHttpRequest",
  "WebSocket",
  "EventSource",
  "navigator",
  "localStorage",
  "sessionStorage",
  "indexedDB",
  "console",
  "window",
  "document",
  "process",
  "globalThis",
  "self",
  "eval",
  "Function",
  "importScripts",
  "postMessage",
  "Image",
].map((name) => ({ name, message: "Le moteur ne fait aucune I/O (packages/engine)." }));

export default tseslint.config(
  {
    ignores: [
      "**/node_modules/**",
      "**/.next/**",
      "**/coverage/**",
      "**/dist/**",
      "**/generated/**",
      "**/next-env.d.ts",
      "**/.venv/**",
      "**/test-results/**",
      "**/playwright-report/**",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["packages/engine/src/**/*.ts"],
    rules: {
      "no-restricted-globals": ["error", ...ENGINE_FORBIDDEN_GLOBALS],
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            { group: ["*", "!./*", "!../*"], message: "Aucun import externe dans le moteur." },
          ],
        },
      ],
    },
  },
  {
    files: ["**/*.mjs", "**/*.cjs", "**/*.js"],
    languageOptions: { globals: { process: "readonly", console: "readonly", URL: "readonly" } },
  },
);
