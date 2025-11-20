<script lang="ts">
  import { neuroforgeApi } from "$lib/api/neuroforge";
  import { onMount } from "svelte";
  import type { DomainConfig, PromptTemplate } from "$lib/types";
  import Button from "$lib/components/Button.svelte";
  import Alert from "$lib/components/Alert.svelte";

  let domains: DomainConfig[] = [];
  let selectedDomain: DomainConfig | null = null;
  let loading = true;
  let error: string | null = null;
  let successMessage: string | null = null;
  let selectedTab: "config" | "templates" | "rubric" = "config";

  onMount(async () => {
    await loadDomains();
  });

  async function loadDomains() {
    try {
      loading = true;
      error = null;
      const response = await neuroforgeApi.fetchDomains();
      if (response.success && response.data) {
        domains = response.data;
        if (domains.length > 0 && !selectedDomain) {
          selectedDomain = domains[0];
        }
      } else {
        error = response.error?.message || "Failed to load domains";
      }
    } catch (err: any) {
      error = err.message || "An error occurred";
    } finally {
      loading = false;
    }
  }

  function clearMessages() {
    error = null;
    successMessage = null;
  }

  function getDomainLabel(domainName: string): string {
    const labels: Record<string, string> = {
      literary: "📚 Literary",
      market: "📈 Market",
      general: "🔧 General",
      support: "🤝 Support",
    };
    return labels[domainName] || domainName;
  }

  function getCategoryIcon(category: string): string {
    const icons: Record<string, string> = {
      system: "⚙️",
      user: "👤",
      context: "📖",
    };
    return icons[category] || "📄";
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div>
    <h1 class="text-3xl font-bold text-forge-ink-900 dark:text-forge-ash-50">
      Domains & Adapters
    </h1>
    <p class="mt-1 text-forge-ash-600 dark:text-forge-ash-400">
      Configure domain-specific settings, prompt templates, and policies
    </p>
  </div>

  <!-- Messages -->
  {#if error}
    <Alert type="error" message={error} onDismiss={clearMessages} />
  {/if}
  {#if successMessage}
    <Alert type="success" message={successMessage} onDismiss={clearMessages} />
  {/if}

  <!-- Main Content -->
  <div class="grid grid-cols-4 gap-6">
    <!-- Domain List -->
    <div class="col-span-1 space-y-2">
      <h3
        class="px-3 py-2 text-xs font-semibold text-forge-ash-600 dark:text-forge-ash-400 uppercase"
      >
        Available Domains
      </h3>
      {#if loading}
        <div class="space-y-2">
          {#each [1, 2, 3] as _}
            <div
              class="h-10 animate-pulse rounded bg-forge-ash-200 dark:bg-forge-ash-700"
            />
          {/each}
        </div>
      {:else}
        <div
          class="space-y-1 rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-2 dark:border-forge-ash-700 dark:bg-forge-ash-800"
        >
          {#each domains as domain (domain.id)}
            <button
              on:click={() => (selectedDomain = domain)}
              class={`w-full rounded-md px-3 py-2 text-left text-sm font-medium transition ${
                selectedDomain?.id === domain.id
                  ? "bg-forge-ember-600 text-white dark:bg-forge-ember-700"
                  : "text-forge-ink-900 hover:bg-forge-ash-200 dark:text-forge-ash-50 dark:hover:bg-forge-ash-700"
              }`}
            >
              {getDomainLabel(domain.name)}
            </button>
          {/each}
        </div>
      {/if}
    </div>

    <!-- Domain Detail -->
    <div class="col-span-3 space-y-4">
      {#if loading}
        <div
          class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-6 dark:border-forge-ash-700 dark:bg-forge-ash-900"
        >
          <div class="space-y-3">
            {#each [1, 2, 3] as _}
              <div
                class="h-6 animate-pulse rounded bg-forge-ash-200 dark:bg-forge-ash-700"
              />
            {/each}
          </div>
        </div>
      {:else if selectedDomain}
        <!-- Domain Info Card -->
        <div
          class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-6 dark:border-forge-ash-700 dark:bg-forge-ash-900"
        >
          <div>
            <h2
              class="text-2xl font-bold text-forge-ink-900 dark:text-forge-ash-50"
            >
              {getDomainLabel(selectedDomain.name)}
            </h2>
            <p class="mt-1 text-sm text-forge-ash-600 dark:text-forge-ash-400">
              {selectedDomain.description || "No description provided"}
            </p>
          </div>

          <!-- Tabs -->
          <div
            class="mt-6 border-b border-forge-ash-200 dark:border-forge-ash-700"
          >
            <div class="flex space-x-6">
              {#each [{ id: "config", label: "Configuration" }, { id: "templates", label: "Prompt Templates" }, { id: "rubric", label: "Evaluation Rubric" }] as tab}
                <button
                  on:click={() => (selectedTab = tab.id as "config" | "templates" | "rubric")}
                  class={`border-b-2 px-1 py-3 text-sm font-medium transition ${
                    selectedTab === tab.id
                      ? "border-forge-ember-600 text-forge-ember-600 dark:border-forge-ember-400 dark:text-forge-ember-400"
                      : "border-transparent text-forge-ash-600 hover:text-forge-ink-900 dark:text-forge-ash-400 dark:hover:text-forge-ash-50"
                  }`}
                >
                  {tab.label}
                </button>
              {/each}
            </div>
          </div>

          <!-- Tab Content -->
          <div class="mt-6 space-y-4">
            {#if selectedTab === "config"}
              <!-- Configuration Tab -->
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <p
                    class="text-xs font-medium text-forge-ash-600 dark:text-forge-ash-400"
                  >
                    Domain Name
                  </p>
                  <p
                    class="mt-1 font-medium text-forge-ink-900 dark:text-forge-ash-50"
                  >
                    {selectedDomain.name}
                  </p>
                </div>
                <div>
                  <p
                    class="text-xs font-medium text-forge-ash-600 dark:text-forge-ash-400"
                  >
                    Label
                  </p>
                  <p
                    class="mt-1 font-medium text-forge-ink-900 dark:text-forge-ash-50"
                  >
                    {selectedDomain.label}
                  </p>
                </div>
              </div>

              <!-- Policy Tokens -->
              <div
                class="border-t border-forge-ash-200 pt-4 dark:border-forge-ash-700"
              >
                <h4
                  class="text-sm font-semibold text-forge-ink-900 dark:text-forge-ash-50"
                >
                  Policy Tokens
                </h4>
                <div class="mt-2 flex flex-wrap gap-2">
                  {#each selectedDomain.policyTokens as token}
                    <span
                      class="rounded-full bg-forge-brass-100 px-3 py-1 text-xs font-medium text-forge-brass-800 dark:bg-forge-brass-900 dark:text-forge-brass-200"
                    >
                      {token}
                    </span>
                  {/each}
                </div>
              </div>

              <!-- Context Scopes -->
              <div
                class="border-t border-forge-ash-200 pt-4 dark:border-forge-ash-700"
              >
                <h4
                  class="text-sm font-semibold text-forge-ink-900 dark:text-forge-ash-50"
                >
                  Context Scopes
                </h4>
                <div class="mt-2 space-y-1">
                  {#each selectedDomain.contextScopes as scope}
                    <p
                      class="text-sm text-forge-ash-700 dark:text-forge-ash-300"
                    >
                      • {scope}
                    </p>
                  {/each}
                </div>
              </div>
            {:else if selectedTab === "templates"}
              <!-- Prompt Templates Tab -->
              <div class="space-y-3">
                {#if selectedDomain.promptTemplates.length === 0}
                  <p class="text-sm text-forge-ash-600 dark:text-forge-ash-400">
                    No prompt templates configured for this domain.
                  </p>
                {:else}
                  {#each selectedDomain.promptTemplates as template (template.id)}
                    <div
                      class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-4 dark:border-forge-ash-700 dark:bg-forge-ash-800"
                    >
                      <div class="flex items-start justify-between">
                        <div>
                          <div class="flex items-center gap-2">
                            <span class="text-lg"
                              >{getCategoryIcon(template.category)}</span
                            >
                            <h5
                              class="font-medium text-forge-ink-900 dark:text-forge-ash-50"
                            >
                              {template.name}
                            </h5>
                            <span
                              class="text-xs font-medium text-forge-ash-600 dark:text-forge-ash-400"
                            >
                              {template.category}
                            </span>
                          </div>
                          <p
                            class="mt-2 whitespace-pre-wrap rounded bg-forge-ink-900 p-2 font-mono text-xs text-forge-ash-100 dark:bg-forge-ash-900 dark:text-forge-ash-300"
                          >
                            {template.template}
                          </p>
                          <div class="mt-2 flex gap-1">
                            {#each template.variables as variable}
                              <span
                                class="rounded bg-forge-brass-200 px-2 py-1 text-xs text-forge-brass-900 dark:bg-forge-brass-700 dark:text-forge-brass-100"
                              >
                                {"{" + variable + "}"}
                              </span>
                            {/each}
                          </div>
                        </div>
                      </div>
                    </div>
                  {/each}
                {/if}
              </div>
            {:else if selectedTab === "rubric"}
              <!-- Evaluation Rubric Tab -->
              <div class="space-y-3">
                {#if selectedDomain.evaluationRubric.length === 0}
                  <p class="text-sm text-forge-ash-600 dark:text-forge-ash-400">
                    No evaluation rubric configured for this domain.
                  </p>
                {:else}
                  {#each selectedDomain.evaluationRubric as dimension (dimension.name)}
                    <div
                      class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-4 dark:border-forge-ash-700 dark:bg-forge-ash-800"
                    >
                      <div class="flex items-start justify-between">
                        <div class="flex-1">
                          <h5
                            class="font-medium text-forge-ink-900 dark:text-forge-ash-50"
                          >
                            {dimension.name}
                          </h5>
                          <p
                            class="mt-1 text-sm text-forge-ash-700 dark:text-forge-ash-300"
                          >
                            {dimension.description}
                          </p>
                          <div class="mt-3">
                            <p
                              class="text-xs font-medium text-forge-ash-600 dark:text-forge-ash-400"
                            >
                              Rubric Items:
                            </p>
                            <ul class="mt-1 space-y-1">
                              {#each dimension.rubric as item}
                                <li
                                  class="text-sm text-forge-ash-700 dark:text-forge-ash-300"
                                >
                                  • {item}
                                </li>
                              {/each}
                            </ul>
                          </div>
                        </div>
                        <div
                          class="ml-4 rounded-lg bg-forge-ember-100 px-3 py-2 text-center dark:bg-forge-ember-900"
                        >
                          <p
                            class="text-xs font-medium text-forge-ash-600 dark:text-forge-ash-400"
                          >
                            Weight
                          </p>
                          <p
                            class="mt-1 text-lg font-bold text-forge-ember-600 dark:text-forge-ember-400"
                          >
                            {(dimension.weight * 100).toFixed(0)}%
                          </p>
                        </div>
                      </div>
                    </div>
                  {/each}
                {/if}
              </div>
            {/if}
          </div>
        </div>
      {:else}
        <div
          class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-12 text-center dark:border-forge-ash-700 dark:bg-forge-ash-900"
        >
          <p class="text-forge-ash-600 dark:text-forge-ash-400">
            No domains available
          </p>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
</style>
