export default {
  root: true,
  parser: "@typescript-eslint/parser",
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:svelte/recommended",
    "prettier"
  ],
  plugins: ["@typescript-eslint", "svelte"],
  overrides: [
    {
      files: ["*.svelte"],
      processor: "svelte/svelte"
    }
  ],
  rules: {
    // Your custom rules here
    "@typescript-eslint/no-unused-vars": ["warn"],
    "svelte/no-at-html-tags": "error"
  }
};
