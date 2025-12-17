
import { defineConfig } from "eslint/config";
import js from "@eslint/js";
import tseslint from "@typescript-eslint/eslint-plugin";
import tsparser from "@typescript-eslint/parser";
import svelte from "eslint-plugin-svelte";
import prettier from "eslint-config-prettier";

export default defineConfig([
  // Ignore patterns (migrated from .eslintignore and .gitignore)
  {
    ignores: ["**/node_modules/**"]
  },
  js.configs.recommended,
  {
    files: ["**/*.ts", "**/*.tsx"],
    languageOptions: {
      parser: tsparser,
    },
    plugins: {
      "@typescript-eslint": tseslint,
    },
    rules: {
      ...tseslint.configs.recommended.rules,
      "@typescript-eslint/no-unused-vars": ["warn"],
    },
  },
  {
    files: ["**/*.svelte"],
    plugins: {
      svelte,
    },
    rules: {
      ...svelte.configs.recommended.rules,
      "svelte/no-at-html-tags": "error"
    },
    processor: svelte.processors.svelte,
  },
  prettier,
]);
