<script lang="ts">
  import "../app.css";
  import { theme, appState, preferences } from "$lib/stores";
  import { onMount } from "svelte";
  import type { LayoutData } from "./$types";

  let mounted = false;
  let currentTheme: "light" | "dark" = "dark";

  // Function to apply theme to DOM
  function applyTheme(themeValue: "light" | "dark") {
    if (typeof document !== "undefined") {
      currentTheme = themeValue;

      // Update the data attribute for CSS targeting
      document.documentElement.setAttribute("data-theme", themeValue);

      // Update the class for Tailwind dark: prefix
      if (themeValue === "dark") {
        document.documentElement.classList.add("dark");
      } else {
        document.documentElement.classList.remove("dark");
      }

      // Optional: Update meta theme-color
      const metaThemeColor = document.querySelector('meta[name="theme-color"]');
      if (metaThemeColor) {
        metaThemeColor.setAttribute(
          "content",
          themeValue === "dark" ? "#0C0C0E" : "#F5F5F7"
        );
      }
    }
  }

  onMount(() => {
    // Load user preferences from localStorage
    preferences.load();

    // Load and apply theme from localStorage or system preference
    theme.init();

    // Mark as mounted first
    mounted = true;

    // Subscribe to theme changes and apply them to the DOM
    // This will fire immediately with the current theme value after init()
    const unsubscribe = theme.subscribe((value: "light" | "dark") => {
      applyTheme(value);
    });

    // Cleanup subscription on component destroy
    return unsubscribe;
  });
</script>

{#if mounted}
  <div
    class="flex h-screen bg-forge-ash-50 dark:bg-forge-ash-900 text-forge-ink-900 dark:text-forge-ink-50 transition-colors duration-300"
    data-theme={currentTheme}
  >
    <!-- Left Navigation Rail -->
    <nav
      class="w-64 bg-forge-ash-100 dark:bg-forge-ash-800 border-r border-forge-brass-300 dark:border-forge-brass-700 flex flex-col"
    >
      <!-- Logo -->
      <div
        class="p-4 border-b border-forge-brass-300 dark:border-forge-brass-700"
      >
        <h1 class="text-2xl font-bold text-forge-ember-600">NeuroForge</h1>
        <p class="text-xs text-forge-ink-600 dark:text-forge-ink-400">
          Control Cockpit
        </p>
      </div>

      <!-- Navigation Links -->
      <div class="flex-1 overflow-y-auto p-4">
        <ul class="space-y-2">
          <li>
            <a
              href="/overview"
              class="block px-3 py-2 rounded-md hover:bg-forge-brass-200 dark:hover:bg-forge-brass-700 transition"
              >Overview</a
            >
          </li>
          <li>
            <a
              href="/pipelines"
              class="block px-3 py-2 rounded-md hover:bg-forge-brass-200 dark:hover:bg-forge-brass-700 transition"
              >Pipelines</a
            >
          </li>
          <li>
            <a
              href="/domains"
              class="block px-3 py-2 rounded-md hover:bg-forge-brass-200 dark:hover:bg-forge-brass-700 transition"
              >Domains</a
            >
          </li>
          <li>
            <a
              href="/models"
              class="block px-3 py-2 rounded-md hover:bg-forge-brass-200 dark:hover:bg-forge-brass-700 transition"
              >Models</a
            >
          </li>
          <li>
            <a
              href="/evaluations"
              class="block px-3 py-2 rounded-md hover:bg-forge-brass-200 dark:hover:bg-forge-brass-700 transition"
              >Evaluations</a
            >
          </li>
          <li>
            <a
              href="/logs"
              class="block px-3 py-2 rounded-md hover:bg-forge-brass-200 dark:hover:bg-forge-brass-700 transition"
              >Logs</a
            >
          </li>
          <li>
            <a
              href="/playground"
              class="block px-3 py-2 rounded-md hover:bg-forge-brass-200 dark:hover:bg-forge-brass-700 transition"
              >Playground</a
            >
          </li>
          <li>
            <a
              href="/analytics"
              class="block px-3 py-2 rounded-md hover:bg-forge-brass-200 dark:hover:bg-forge-brass-700 transition"
              >Analytics</a
            >
          </li>
        </ul>
      </div>

      <!-- Settings -->
      <div
        class="p-4 border-t border-forge-brass-300 dark:border-forge-brass-700"
      >
        <a
          href="/settings"
          class="block px-3 py-2 rounded-md hover:bg-forge-brass-200 dark:hover:bg-forge-brass-700 transition"
          >⚙️ Settings</a
        >
      </div>
    </nav>

    <!-- Main Content -->
    <div class="flex-1 flex flex-col">
      <!-- Top App Bar -->
      <header
        class="bg-forge-ash-100 dark:bg-forge-ash-800 border-b border-forge-brass-300 dark:border-forge-brass-700 px-6 py-4 flex items-center justify-between"
      >
        <div class="flex items-center gap-4">
          <h2 class="text-lg font-semibold">NeuroForge Dashboard</h2>
          <span
            class="text-xs px-2 py-1 rounded-full bg-forge-ember-200 dark:bg-forge-ember-900 text-forge-ember-800 dark:text-forge-ember-200"
          >
            {$appState.environment.toUpperCase()}
          </span>
        </div>

        <div class="flex items-center gap-4">
          <!-- Theme Toggle -->
          <button
            on:click={() => theme.toggle()}
            aria-label={`Switch to ${
              $theme === "dark" ? "light" : "dark"
            } mode`}
            class="p-2 rounded-md hover:bg-forge-brass-200 dark:hover:bg-forge-brass-700 transition"
          >
            {$theme === "light" ? "🌙" : "☀️"}
          </button>

          <!-- User Menu -->
          <div
            class="px-3 py-1 rounded-md bg-forge-brass-200 dark:bg-forge-brass-700 text-sm"
          >
            User
          </div>
        </div>
      </header>

      <!-- Page Content -->
      <main class="flex-1 overflow-auto p-6">
        <slot />
      </main>
    </div>
  </div>
{/if}

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    overflow: hidden;
  }

  :global(html) {
    overflow: hidden;
  }
</style>
