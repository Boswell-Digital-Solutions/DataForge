<script lang="ts">
  import { theme, preferences, toggleTheme } from "$lib/stores";
  import { Domain } from "$lib/types";
  import Button from "$lib/components/Button.svelte";
  import Alert from "$lib/components/Alert.svelte";

  let isDirty = false;
  let successMessage: string | null = null;

  let formData = {
    defaultDomain: Domain.LITERARY as Domain,
    defaultModelProvider: "ollama",
    autoRefreshEnabled: true,
    refreshIntervalMs: 5000,
    maxRowsPerTable: 50,
    compactMode: false,
  };

  let envSettings = {
    environment: "development",
    apiBaseUrl: "http://localhost:8000/api/v1",
    features: {
      enableMetrics: true,
      enableTracing: true,
      enableCaching: true,
      enableEvaluation: true,
    },
  };

  let advancedSettings = {
    maxTokens: 8000,
    contextTTL: 3600,
    requestTimeout: 30000,
    rateLimitPerMinute: 60,
    cacheTTL: 300000,
  };

  function handleSave() {
    preferences.save(formData);
    isDirty = false;
    successMessage = "Settings saved successfully!";
    setTimeout(() => (successMessage = null), 3000);
  }

  function handleReset() {
    isDirty = false;
    successMessage = null;
  }

  function toggleFeature(feature: string) {
    envSettings.features = {
      ...envSettings.features,
      [feature]:
        !envSettings.features[feature as keyof typeof envSettings.features],
    };
    isDirty = true;
  }

  function clearMessages() {
    successMessage = null;
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div>
    <h1 class="text-3xl font-bold text-forge-ink-900 dark:text-forge-ash-50">
      Settings
    </h1>
    <p class="mt-1 text-forge-ash-600 dark:text-forge-ash-400">
      Configure environment, features, and preferences
    </p>
  </div>

  <!-- Messages -->
  {#if successMessage}
    <Alert type="success" message={successMessage} onDismiss={clearMessages} />
  {/if}

  <!-- Settings Tabs -->
  <div class="space-y-6">
    <!-- Appearance Section -->
    <div
      class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-6 dark:border-forge-ash-700 dark:bg-forge-ash-900"
    >
      <h2
        class="text-lg font-semibold text-forge-ink-900 dark:text-forge-ash-50"
      >
        Appearance
      </h2>
      <p class="mt-1 text-sm text-forge-ash-600 dark:text-forge-ash-400">
        Customize how NeuroForge looks and feels
      </p>

      <div class="mt-6 space-y-4">
        <!-- Theme Toggle -->
        <div class="flex items-center justify-between">
          <div>
            <p class="font-medium text-forge-ink-900 dark:text-forge-ash-50">
              Dark Mode
            </p>
            <p class="text-sm text-forge-ash-600 dark:text-forge-ash-400">
              Toggle between light and dark theme
            </p>
          </div>
          <button
            on:click={() => toggleTheme()}
            aria-label={`Switch to ${
              $theme === "dark" ? "light" : "dark"
            } mode`}
            class={`relative inline-flex h-8 w-14 items-center rounded-full transition ${
              $theme === "dark"
                ? "bg-forge-ember-600 dark:bg-forge-ember-700"
                : "bg-forge-ash-300 dark:bg-forge-ash-600"
            }`}
          >
            <span
              class={`inline-block h-6 w-6 transform rounded-full bg-white transition ${
                $theme === "dark" ? "translate-x-7" : "translate-x-1"
              }`}
            />
          </button>
        </div>

        <!-- Compact Mode -->
        <div
          class="flex items-center justify-between border-t border-forge-ash-200 pt-4 dark:border-forge-ash-700"
        >
          <div>
            <p class="font-medium text-forge-ink-900 dark:text-forge-ash-50">
              Compact Mode
            </p>
            <p class="text-sm text-forge-ash-600 dark:text-forge-ash-400">
              Reduce spacing and padding in tables and lists
            </p>
          </div>
          <input
            type="checkbox"
            bind:checked={formData.compactMode}
            on:change={() => (isDirty = true)}
            class="h-4 w-4"
          />
        </div>
      </div>
    </div>

    <!-- Preferences Section -->
    <div
      class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-6 dark:border-forge-ash-700 dark:bg-forge-ash-900"
    >
      <h2
        class="text-lg font-semibold text-forge-ink-900 dark:text-forge-ash-50"
      >
        Preferences
      </h2>
      <p class="mt-1 text-sm text-forge-ash-600 dark:text-forge-ash-400">
        Set default values and behavior
      </p>

      <div class="mt-6 grid grid-cols-2 gap-6">
        <!-- Default Domain -->
        <div>
          <label
            for="domain"
            class="block text-sm font-medium text-forge-ink-900 dark:text-forge-ash-50"
          >
            Default Domain
          </label>
          <select
            id="domain"
            bind:value={formData.defaultDomain}
            on:change={() => (isDirty = true)}
            class="mt-2 w-full rounded-lg border border-forge-ash-300 bg-forge-ash-50 px-4 py-2 text-forge-ink-900 dark:border-forge-ash-600 dark:bg-forge-ash-800 dark:text-forge-ash-50"
          >
            <option value={Domain.LITERARY}>Literary</option>
            <option value={Domain.MARKET}>Market</option>
            <option value={Domain.GENERAL}>General</option>
          </select>
        </div>

        <!-- Default Model Provider -->
        <div>
          <label
            for="provider"
            class="block text-sm font-medium text-forge-ink-900 dark:text-forge-ash-50"
          >
            Default Model Provider
          </label>
          <select
            id="provider"
            bind:value={formData.defaultModelProvider}
            on:change={() => (isDirty = true)}
            class="mt-2 w-full rounded-lg border border-forge-ash-300 bg-forge-ash-50 px-4 py-2 text-forge-ink-900 dark:border-forge-ash-600 dark:bg-forge-ash-800 dark:text-forge-ash-50"
          >
            <option value="ollama">Ollama (Local)</option>
            <option value="anthropic">Anthropic Claude</option>
            <option value="openai">OpenAI GPT</option>
          </select>
        </div>

        <!-- Max Rows Per Table -->
        <div>
          <label
            for="rows"
            class="block text-sm font-medium text-forge-ink-900 dark:text-forge-ash-50"
          >
            Max Rows Per Table
          </label>
          <input
            id="rows"
            type="number"
            bind:value={formData.maxRowsPerTable}
            on:change={() => (isDirty = true)}
            min="10"
            max="500"
            class="mt-2 w-full rounded-lg border border-forge-ash-300 bg-forge-ash-50 px-4 py-2 text-forge-ink-900 dark:border-forge-ash-600 dark:bg-forge-ash-800 dark:text-forge-ash-50"
          />
        </div>

        <!-- Refresh Interval -->
        <div>
          <label
            for="interval"
            class="block text-sm font-medium text-forge-ink-900 dark:text-forge-ash-50"
          >
            Auto-Refresh Interval (ms)
          </label>
          <input
            id="interval"
            type="number"
            bind:value={formData.refreshIntervalMs}
            on:change={() => (isDirty = true)}
            min="1000"
            step="1000"
            class="mt-2 w-full rounded-lg border border-forge-ash-300 bg-forge-ash-50 px-4 py-2 text-forge-ink-900 dark:border-forge-ash-600 dark:bg-forge-ash-800 dark:text-forge-ash-50"
          />
        </div>
      </div>

      <!-- Auto-Refresh Toggle -->
      <div
        class="mt-4 flex items-center justify-between border-t border-forge-ash-200 pt-4 dark:border-forge-ash-700"
      >
        <div>
          <p class="font-medium text-forge-ink-900 dark:text-forge-ash-50">
            Auto-Refresh Enabled
          </p>
          <p class="text-sm text-forge-ash-600 dark:text-forge-ash-400">
            Automatically refresh data at set interval
          </p>
        </div>
        <input
          type="checkbox"
          bind:checked={formData.autoRefreshEnabled}
          on:change={() => (isDirty = true)}
          class="h-4 w-4"
        />
      </div>
    </div>

    <!-- Feature Flags Section -->
    <div
      class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-6 dark:border-forge-ash-700 dark:bg-forge-ash-900"
    >
      <h2
        class="text-lg font-semibold text-forge-ink-900 dark:text-forge-ash-50"
      >
        Feature Flags
      </h2>
      <p class="mt-1 text-sm text-forge-ash-600 dark:text-forge-ash-400">
        Enable or disable experimental features
      </p>

      <div class="mt-6 space-y-4">
        <div class="flex items-center justify-between">
          <div>
            <p class="font-medium text-forge-ink-900 dark:text-forge-ash-50">
              Enable Metrics
            </p>
            <p class="text-sm text-forge-ash-600 dark:text-forge-ash-400">
              Export metrics to Prometheus
            </p>
          </div>
          <input
            type="checkbox"
            checked={envSettings.features.enableMetrics}
            on:change={() => toggleFeature("enableMetrics")}
            class="h-4 w-4"
          />
        </div>

        <div class="flex items-center justify-between">
          <div>
            <p class="font-medium text-forge-ink-900 dark:text-forge-ash-50">
              Enable Tracing
            </p>
            <p class="text-sm text-forge-ash-600 dark:text-forge-ash-400">
              Enable request tracing and correlation IDs
            </p>
          </div>
          <input
            type="checkbox"
            checked={envSettings.features.enableTracing}
            on:change={() => toggleFeature("enableTracing")}
            class="h-4 w-4"
          />
        </div>

        <div class="flex items-center justify-between">
          <div>
            <p class="font-medium text-forge-ink-900 dark:text-forge-ash-50">
              Enable Caching
            </p>
            <p class="text-sm text-forge-ash-600 dark:text-forge-ash-400">
              Enable result caching and optimization
            </p>
          </div>
          <input
            type="checkbox"
            checked={envSettings.features.enableCaching}
            on:change={() => toggleFeature("enableCaching")}
            class="h-4 w-4"
          />
        </div>

        <div class="flex items-center justify-between">
          <div>
            <p class="font-medium text-forge-ink-900 dark:text-forge-ash-50">
              Enable Evaluation
            </p>
            <p class="text-sm text-forge-ash-600 dark:text-forge-ash-400">
              Enable LLM-based evaluation scoring
            </p>
          </div>
          <input
            type="checkbox"
            checked={envSettings.features.enableEvaluation}
            on:change={() => toggleFeature("enableEvaluation")}
            class="h-4 w-4"
          />
        </div>
      </div>
    </div>

    <!-- Advanced Settings Section -->
    <div
      class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-6 dark:border-forge-ash-700 dark:bg-forge-ash-900"
    >
      <h2
        class="text-lg font-semibold text-forge-ink-900 dark:text-forge-ash-50"
      >
        Advanced Settings
      </h2>
      <p class="mt-1 text-sm text-forge-ash-600 dark:text-forge-ash-400">
        Configure pipeline and performance parameters
      </p>

      <div class="mt-6 grid grid-cols-2 gap-6">
        <div>
          <label
            for="maxTokens"
            class="block text-sm font-medium text-forge-ink-900 dark:text-forge-ash-50"
          >
            Max Context Tokens
          </label>
          <input
            id="maxTokens"
            type="number"
            bind:value={advancedSettings.maxTokens}
            min="1000"
            step="1000"
            class="mt-2 w-full rounded-lg border border-forge-ash-300 bg-forge-ash-50 px-4 py-2 text-forge-ink-900 dark:border-forge-ash-600 dark:bg-forge-ash-800 dark:text-forge-ash-50"
            disabled
          />
          <p class="mt-1 text-xs text-forge-ash-600 dark:text-forge-ash-400">
            Read-only (configured server-side)
          </p>
        </div>

        <div>
          <label
            for="contextTTL"
            class="block text-sm font-medium text-forge-ink-900 dark:text-forge-ash-50"
          >
            Context Cache TTL (seconds)
          </label>
          <input
            id="contextTTL"
            type="number"
            bind:value={advancedSettings.contextTTL}
            min="60"
            step="60"
            class="mt-2 w-full rounded-lg border border-forge-ash-300 bg-forge-ash-50 px-4 py-2 text-forge-ink-900 dark:border-forge-ash-600 dark:bg-forge-ash-800 dark:text-forge-ash-50"
            disabled
          />
          <p class="mt-1 text-xs text-forge-ash-600 dark:text-forge-ash-400">
            Read-only (configured server-side)
          </p>
        </div>

        <div>
          <label
            for="timeout"
            class="block text-sm font-medium text-forge-ink-900 dark:text-forge-ash-50"
          >
            Request Timeout (ms)
          </label>
          <input
            id="timeout"
            type="number"
            bind:value={advancedSettings.requestTimeout}
            min="5000"
            step="1000"
            class="mt-2 w-full rounded-lg border border-forge-ash-300 bg-forge-ash-50 px-4 py-2 text-forge-ink-900 dark:border-forge-ash-600 dark:bg-forge-ash-800 dark:text-forge-ash-50"
            disabled
          />
          <p class="mt-1 text-xs text-forge-ash-600 dark:text-forge-ash-400">
            Read-only (configured server-side)
          </p>
        </div>

        <div>
          <label
            for="rateLimit"
            class="block text-sm font-medium text-forge-ink-900 dark:text-forge-ash-50"
          >
            Rate Limit (req/min)
          </label>
          <input
            id="rateLimit"
            type="number"
            bind:value={advancedSettings.rateLimitPerMinute}
            min="1"
            class="mt-2 w-full rounded-lg border border-forge-ash-300 bg-forge-ash-50 px-4 py-2 text-forge-ink-900 dark:border-forge-ash-600 dark:bg-forge-ash-800 dark:text-forge-ash-50"
            disabled
          />
          <p class="mt-1 text-xs text-forge-ash-600 dark:text-forge-ash-400">
            Read-only (configured server-side)
          </p>
        </div>
      </div>
    </div>

    <!-- Environment Info -->
    <div
      class="rounded-lg border border-forge-brass-200 bg-forge-brass-50 p-6 dark:border-forge-brass-700 dark:bg-forge-ash-800"
    >
      <h2
        class="text-lg font-semibold text-forge-ink-900 dark:text-forge-ash-50"
      >
        Environment
      </h2>

      <div class="mt-4 grid grid-cols-2 gap-4">
        <div>
          <p
            class="text-xs font-medium text-forge-ash-600 dark:text-forge-ash-400"
          >
            Environment
          </p>
          <p
            class="mt-1 rounded-lg bg-forge-ash-50 px-3 py-2 font-mono text-sm dark:bg-forge-ash-900"
          >
            {envSettings.environment}
          </p>
        </div>
        <div>
          <p
            class="text-xs font-medium text-forge-ash-600 dark:text-forge-ash-400"
          >
            API Base URL
          </p>
          <p
            class="mt-1 rounded-lg bg-forge-ash-50 px-3 py-2 font-mono text-sm dark:bg-forge-ash-900"
          >
            {envSettings.apiBaseUrl}
          </p>
        </div>
      </div>
    </div>
  </div>

  <!-- Action Buttons -->
  <div class="flex justify-end gap-3">
    {#if isDirty}
      <Button variant="secondary" on:click={handleReset}>Cancel</Button>
      <Button variant="primary" on:click={handleSave}>Save Changes</Button>
    {:else}
      <p class="text-sm text-forge-ash-600 dark:text-forge-ash-400">
        All settings saved
      </p>
    {/if}
  </div>
</div>

<style>
</style>
