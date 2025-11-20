<script lang="ts">
  import { neuroforgeApi } from "$lib/api/neuroforge";
  import { onMount } from "svelte";
  import type { PipelineConfig } from "$lib/types";
  import Button from "$lib/components/Button.svelte";
  import Alert from "$lib/components/Alert.svelte";

  let pipelines: PipelineConfig[] = [];
  let selectedPipeline: PipelineConfig | null = null;
  let loading = true;
  let error: string | null = null;
  let successMessage: string | null = null;
  let showCreateModal = false;
  let sortColumn: keyof PipelineConfig = "name";
  let sortAsc = true;

  onMount(async () => {
    await loadPipelines();
  });

  async function loadPipelines() {
    try {
      loading = true;
      error = null;
      const response = await neuroforgeApi.fetchPipelines();
      if (response.success && response.data) {
        pipelines = response.data;
      } else {
        error = response.error?.message || "Failed to load pipelines";
      }
    } catch (err: any) {
      error = err.message || "An error occurred";
    } finally {
      loading = false;
    }
  }

  function sortBy(column: keyof PipelineConfig) {
    if (sortColumn === column) {
      sortAsc = !sortAsc;
    } else {
      sortColumn = column;
      sortAsc = true;
    }
  }

  $: sortedPipelines = [...pipelines].sort((a, b) => {
    const aVal = a[sortColumn];
    const bVal = b[sortColumn];
    const cmp = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
    return sortAsc ? cmp : -cmp;
  });

  function clearMessages() {
    error = null;
    successMessage = null;
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-3xl font-bold text-forge-ink-900 dark:text-forge-ash-50">
        Pipelines
      </h1>
      <p class="mt-1 text-forge-ash-600 dark:text-forge-ash-400">
        Configure and manage inference pipelines for your domains
      </p>
    </div>
    <Button on:click={() => (showCreateModal = true)} variant="primary">
      + New Pipeline
    </Button>
  </div>

  <!-- Messages -->
  {#if error}
    <Alert type="error" message={error} onDismiss={clearMessages} />
  {/if}
  {#if successMessage}
    <Alert type="success" message={successMessage} onDismiss={clearMessages} />
  {/if}

  <!-- Main Content -->
  <div class="grid grid-cols-3 gap-6">
    <!-- Pipeline List -->
    <div class="col-span-2 space-y-4">
      {#if loading}
        <div
          class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-6 dark:border-forge-ash-700 dark:bg-forge-ash-900"
        >
          <div class="space-y-3">
            {#each [1, 2, 3] as _}
              <div
                class="h-16 animate-pulse rounded bg-forge-ash-200 dark:bg-forge-ash-700"
              />
            {/each}
          </div>
        </div>
      {:else if pipelines.length === 0}
        <div
          class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-12 text-center dark:border-forge-ash-700 dark:bg-forge-ash-900"
        >
          <p class="text-forge-ash-600 dark:text-forge-ash-400">
            No pipelines yet. Create one to get started.
          </p>
        </div>
      {:else}
        <div
          class="overflow-x-auto rounded-lg border border-forge-ash-200 dark:border-forge-ash-700"
        >
          <table class="w-full">
            <thead
              class="border-b border-forge-ash-200 bg-forge-ash-50 dark:border-forge-ash-700 dark:bg-forge-ash-900"
            >
              <tr>
                <th class="px-6 py-3 text-left">
                  <button
                    on:click={() => sortBy("name")}
                    class="inline-flex items-center gap-2 font-semibold text-forge-ink-900 dark:text-forge-ash-50 hover:text-forge-ember-600"
                  >
                    Name
                    {#if sortColumn === "name"}
                      <span>{sortAsc ? "↑" : "↓"}</span>
                    {/if}
                  </button>
                </th>
                <th class="px-6 py-3 text-left">
                  <button
                    on:click={() => sortBy("domain")}
                    class="inline-flex items-center gap-2 font-semibold text-forge-ink-900 dark:text-forge-ash-50 hover:text-forge-ember-600"
                  >
                    Domain
                    {#if sortColumn === "domain"}
                      <span>{sortAsc ? "↑" : "↓"}</span>
                    {/if}
                  </button>
                </th>
                <th
                  class="px-6 py-3 text-left font-semibold text-forge-ink-900 dark:text-forge-ash-50"
                >
                  Adapter
                </th>
                <th
                  class="px-6 py-3 text-left font-semibold text-forge-ink-900 dark:text-forge-ash-50"
                >
                  Routing
                </th>
                <th
                  class="px-6 py-3 text-left font-semibold text-forge-ink-900 dark:text-forge-ash-50"
                >
                  Models
                </th>
                <th
                  class="px-6 py-3 text-center font-semibold text-forge-ink-900 dark:text-forge-ash-50"
                >
                  Action
                </th>
              </tr>
            </thead>
            <tbody>
              {#each sortedPipelines as pipeline (pipeline.id)}
                <tr
                  class="border-b border-forge-ash-100 hover:bg-forge-ash-50 dark:border-forge-ash-800 dark:hover:bg-forge-ash-800 cursor-pointer transition"
                  on:click={() => (selectedPipeline = pipeline)}
                >
                  <td
                    class="px-6 py-4 font-medium text-forge-ink-900 dark:text-forge-ash-50"
                  >
                    {pipeline.name}
                  </td>
                  <td
                    class="px-6 py-4 text-sm text-forge-ash-600 dark:text-forge-ash-400"
                  >
                    <span
                      class="rounded-full bg-forge-brass-100 px-3 py-1 text-xs font-medium text-forge-brass-800 dark:bg-forge-brass-900 dark:text-forge-brass-200"
                    >
                      {pipeline.domain}
                    </span>
                  </td>
                  <td
                    class="px-6 py-4 text-sm text-forge-ash-600 dark:text-forge-ash-400"
                  >
                    {pipeline.adapterName}
                  </td>
                  <td
                    class="px-6 py-4 text-sm text-forge-ash-600 dark:text-forge-ash-400"
                  >
                    <span
                      class="inline-flex rounded-full bg-forge-ember-100 px-2 py-1 text-xs font-medium text-forge-ember-800 dark:bg-forge-ember-900 dark:text-forge-ember-200"
                    >
                      {pipeline.routingStrategy.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td
                    class="px-6 py-4 text-sm font-semibold text-forge-brass-600 dark:text-forge-brass-400"
                  >
                    {pipeline.models.length}
                  </td>
                  <td class="px-6 py-4 text-center">
                    <button
                      on:click|stopPropagation={() =>
                        (selectedPipeline = pipeline)}
                      class="text-sm font-medium text-forge-ember-600 hover:text-forge-ember-700 dark:text-forge-ember-400 dark:hover:text-forge-ember-300"
                    >
                      View
                    </button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>

    <!-- Detail Panel -->
    <div class="space-y-4">
      {#if selectedPipeline}
        <div
          class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-6 dark:border-forge-ash-700 dark:bg-forge-ash-900"
        >
          <div class="flex items-start justify-between">
            <h3
              class="text-lg font-semibold text-forge-ink-900 dark:text-forge-ash-50"
            >
              {selectedPipeline.name}
            </h3>
            <button
              on:click={() => (selectedPipeline = null)}
              class="text-forge-ash-600 hover:text-forge-ink-900 dark:text-forge-ash-400 dark:hover:text-forge-ash-50"
            >
              ✕
            </button>
          </div>

          <div
            class="mt-4 space-y-3 border-t border-forge-ash-200 pt-4 dark:border-forge-ash-700"
          >
            <div>
              <p
                class="text-xs font-medium text-forge-ash-600 dark:text-forge-ash-400"
              >
                Domain
              </p>
              <p
                class="mt-1 font-medium text-forge-ink-900 dark:text-forge-ash-50"
              >
                {selectedPipeline.domain}
              </p>
            </div>

            <div>
              <p
                class="text-xs font-medium text-forge-ash-600 dark:text-forge-ash-400"
              >
                Description
              </p>
              <p class="mt-1 text-sm text-forge-ink-900 dark:text-forge-ash-50">
                {selectedPipeline.description || "—"}
              </p>
            </div>

            <div>
              <p
                class="text-xs font-medium text-forge-ash-600 dark:text-forge-ash-400"
              >
                Adapter
              </p>
              <p
                class="mt-1 font-medium text-forge-ink-900 dark:text-forge-ash-50"
              >
                {selectedPipeline.adapterName}
              </p>
            </div>

            <div>
              <p
                class="text-xs font-medium text-forge-ash-600 dark:text-forge-ash-400"
              >
                Routing Strategy
              </p>
              <p
                class="mt-1 font-medium text-forge-ink-900 dark:text-forge-ash-50"
              >
                {selectedPipeline.routingStrategy}
              </p>
            </div>

            <div>
              <p
                class="text-xs font-medium text-forge-ash-600 dark:text-forge-ash-400"
              >
                Max Tokens
              </p>
              <p
                class="mt-1 font-medium text-forge-ink-900 dark:text-forge-ash-50"
              >
                {selectedPipeline.maxTokens}
              </p>
            </div>

            <div>
              <p
                class="text-xs font-medium text-forge-ash-600 dark:text-forge-ash-400"
              >
                Context TTL
              </p>
              <p
                class="mt-1 font-medium text-forge-ink-900 dark:text-forge-ash-50"
              >
                {selectedPipeline.contextTTL}s
              </p>
            </div>
          </div>

          <!-- Pipeline Flow Diagram -->
          <div
            class="mt-6 border-t border-forge-ash-200 pt-4 dark:border-forge-ash-700"
          >
            <p
              class="text-xs font-medium text-forge-ash-600 dark:text-forge-ash-400"
            >
              Pipeline Flow
            </p>
            <div
              class="mt-3 flex items-center justify-between text-xs font-medium"
            >
              <div
                class="flex flex-col items-center rounded-lg bg-forge-brass-50 px-3 py-2 dark:bg-forge-brass-900"
              >
                <span class="text-forge-brass-700 dark:text-forge-brass-300"
                  >Context</span
                >
              </div>
              <span class="text-forge-ash-400">→</span>
              <div
                class="flex flex-col items-center rounded-lg bg-forge-ember-50 px-3 py-2 dark:bg-forge-ember-900"
              >
                <span class="text-forge-ember-700 dark:text-forge-ember-300"
                  >Prompt</span
                >
              </div>
              <span class="text-forge-ash-400">→</span>
              <div
                class="flex flex-col items-center rounded-lg bg-forge-brass-50 px-3 py-2 dark:bg-forge-brass-900"
              >
                <span class="text-forge-brass-700 dark:text-forge-brass-300"
                  >Route</span
                >
              </div>
              <span class="text-forge-ash-400">→</span>
              <div
                class="flex flex-col items-center rounded-lg bg-forge-ember-50 px-3 py-2 dark:bg-forge-ember-900"
              >
                <span class="text-forge-ember-700 dark:text-forge-ember-300"
                  >Eval</span
                >
              </div>
            </div>
          </div>

          <!-- Models in Pipeline -->
          <div
            class="mt-6 border-t border-forge-ash-200 pt-4 dark:border-forge-ash-700"
          >
            <p
              class="text-xs font-medium text-forge-ash-600 dark:text-forge-ash-400"
            >
              Models ({selectedPipeline.models.length})
            </p>
            <div class="mt-2 space-y-2">
              {#each selectedPipeline.models as model (model.modelId)}
                <div
                  class="flex items-center justify-between rounded-lg bg-forge-ash-50 px-3 py-2 dark:bg-forge-ash-800"
                >
                  <span
                    class="text-sm font-medium text-forge-ink-900 dark:text-forge-ash-50"
                  >
                    {model.modelId}
                  </span>
                  <span
                    class="text-xs text-forge-ash-600 dark:text-forge-ash-400"
                  >
                    {model.provider} • P{model.priority}
                  </span>
                </div>
              {/each}
            </div>
          </div>
        </div>
      {:else}
        <div
          class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-6 text-center dark:border-forge-ash-700 dark:bg-forge-ash-900"
        >
          <p class="text-forge-ash-600 dark:text-forge-ash-400">
            Select a pipeline to view details
          </p>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
</style>
