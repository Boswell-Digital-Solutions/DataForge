<script lang="ts">
  import { neuroforgeApi } from "$lib/api/neuroforge";
  import StatCard from "$lib/components/StatCard.svelte";
  import { onMount } from "svelte";
  import type { ModelCatalog, ChampionModel } from "$lib/types";

  let models: ModelCatalog[] = [];
  let championModel: ChampionModel | null = null;
  let loading = true;
  let error: string | null = null;

  // Sorting & Filtering
  let sortColumn: keyof ModelCatalog = "name";
  let sortAsc = true;
  let selectedProvider = "";
  let searchTerm = "";

  onMount(async () => {
    try {
      const [modelsResponse, championResponse] = await Promise.all([
        neuroforgeApi.fetchModels(),
        neuroforgeApi.getChampionModels(),
      ]);

      if (modelsResponse.success) {
        models = modelsResponse.data || [];
      } else {
        error = modelsResponse.error?.message || "Failed to load models";
      }

      if (championResponse.success && championResponse.data?.length) {
        championModel = championResponse.data[0] || null;
      }
    } catch (err: any) {
      error = err.message || "An error occurred";
    } finally {
      loading = false;
    }
  });

  function sortBy(column: keyof ModelCatalog) {
    if (sortColumn === column) {
      sortAsc = !sortAsc;
    } else {
      sortColumn = column;
      sortAsc = true;
    }
  }

  // Get unique providers for filter dropdown
  $: providers = [...new Set(models.map((m) => m.provider))].sort();

  // Filter and sort models
  $: filteredModels = models
    .filter((model) => {
      const matchesProvider =
        !selectedProvider || model.provider === selectedProvider;
      const matchesSearch =
        !searchTerm ||
        model.name.toLowerCase().includes(searchTerm.toLowerCase());
      return matchesProvider && matchesSearch;
    })
    .sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];

      if (aVal === undefined || bVal === undefined) return 0;

      let comparison = 0;
      if (typeof aVal === "string" && typeof bVal === "string") {
        comparison = aVal.localeCompare(bVal);
      } else if (typeof aVal === "number" && typeof bVal === "number") {
        comparison = aVal - bVal;
      }

      return sortAsc ? comparison : -comparison;
    });
</script>

<div class="space-y-8">
  <div>
    <h1 class="text-3xl font-bold text-forge-ink-900 dark:text-forge-ash-50">
      Models
    </h1>
    <p class="mt-2 text-forge-ash-600 dark:text-forge-ash-400">
      View and manage deployed models
    </p>
  </div>

  {#if error}
    <div
      class="rounded-lg border border-forge-ember-200 bg-forge-ember-50 p-4 dark:border-forge-ember-800 dark:bg-forge-ember-950"
    >
      <p class="text-forge-ember-800 dark:text-forge-ember-200">{error}</p>
    </div>
  {/if}

  {#if loading}
    <div class="grid grid-cols-4 gap-4">
      {#each { length: 4 } as _}
        <div
          class="h-32 animate-pulse rounded-lg bg-forge-ash-200 dark:bg-forge-ash-700"
        />
      {/each}
    </div>
  {:else if championModel}
    <div
      class="rounded-lg border-2 border-forge-ember-400 bg-gradient-to-br from-forge-ember-50 to-forge-brass-50 p-8 dark:from-forge-ember-950 dark:to-forge-brass-950"
    >
      <div class="flex items-start justify-between">
        <div>
          <h2
            class="text-2xl font-bold text-forge-ink-900 dark:text-forge-ash-50"
          >
            Champion Model
          </h2>
          <p
            class="mt-2 text-lg font-semibold text-forge-ember-600 dark:text-forge-ember-400"
          >
            {championModel.modelId}
          </p>
          <p class="mt-4 max-w-2xl text-forge-ash-700 dark:text-forge-ash-300">
            Domain: <span
              class="font-bold text-forge-brass-600 dark:text-forge-brass-400"
            >
              {championModel.domain}
            </span>
            · Score:
            <span
              class="font-bold text-forge-brass-600 dark:text-forge-brass-400"
            >
              {(championModel.score * 100).toFixed(1)}%
            </span>
            · Promoted:
            <span
              class="font-bold text-forge-brass-600 dark:text-forge-brass-400"
            >
              {new Date(championModel.promotedAt).toLocaleDateString()}
            </span>
          </p>
        </div>
        <div class="text-6xl">🏆</div>
      </div>
    </div>
  {/if}

  <div>
    <h3 class="text-xl font-semibold text-forge-ink-900 dark:text-forge-ash-50">
      All Models
    </h3>

    {#if models.length > 0}
      <!-- Filters & Search -->
      <div class="mt-4 flex gap-4">
        <input
          type="text"
          placeholder="Search models..."
          bind:value={searchTerm}
          class="flex-1 rounded-lg border border-forge-ash-300 bg-forge-ash-50 px-4 py-2 text-sm text-forge-ink-900 placeholder-forge-ash-500 dark:border-forge-ash-600 dark:bg-forge-ash-800 dark:text-forge-ash-50 dark:placeholder-forge-ash-400"
        />
        <select
          bind:value={selectedProvider}
          class="rounded-lg border border-forge-ash-300 bg-forge-ash-50 px-4 py-2 text-sm text-forge-ink-900 dark:border-forge-ash-600 dark:bg-forge-ash-800 dark:text-forge-ash-50"
        >
          <option value="">All Providers</option>
          {#each providers as provider}
            <option value={provider}>{provider}</option>
          {/each}
        </select>
      </div>
    {/if}

    {#if models.length > 0}
      <div
        class="mt-4 overflow-x-auto rounded-lg border border-forge-ash-200 dark:border-forge-ash-700"
      >
        <table class="w-full">
          <thead
            class="border-b border-forge-ash-200 bg-forge-ash-50 dark:border-forge-ash-700 dark:bg-forge-ash-900"
          >
            <tr>
              <th
                class="cursor-pointer px-6 py-4 text-left text-sm font-semibold text-forge-ink-900 hover:text-forge-ember-600 dark:text-forge-ash-50 dark:hover:text-forge-ember-400"
                on:click={() => sortBy("name")}
                role="button"
                tabindex="0"
              >
                Model ID
                {#if sortColumn === "name"}
                  <span>{sortAsc ? "↑" : "↓"}</span>
                {/if}
              </th>
              <th
                class="cursor-pointer px-6 py-4 text-left text-sm font-semibold text-forge-ink-900 hover:text-forge-ember-600 dark:text-forge-ash-50 dark:hover:text-forge-ember-400"
                on:click={() => sortBy("provider")}
                role="button"
                tabindex="0"
              >
                Provider
                {#if sortColumn === "provider"}
                  <span>{sortAsc ? "↑" : "↓"}</span>
                {/if}
              </th>
              <th
                class="cursor-pointer px-6 py-4 text-left text-sm font-semibold text-forge-ink-900 hover:text-forge-ember-600 dark:text-forge-ash-50 dark:hover:text-forge-ember-400"
                on:click={() => sortBy("health")}
                role="button"
                tabindex="0"
              >
                Avg Latency
                {#if sortColumn === "health"}
                  <span>{sortAsc ? "↑" : "↓"}</span>
                {/if}
              </th>
              <th
                class="px-6 py-4 text-left text-sm font-semibold text-forge-ink-900 dark:text-forge-ash-50"
              >
                Avg Score
              </th>
              <th
                class="px-6 py-4 text-left text-sm font-semibold text-forge-ink-900 dark:text-forge-ash-50"
              >
                Status
              </th>
            </tr>
          </thead>
          <tbody>
            {#each filteredModels as model}
              <tr
                class="border-b border-forge-ash-100 hover:bg-forge-ash-50 dark:border-forge-ash-800 dark:hover:bg-forge-ash-800"
              >
                <td
                  class="px-6 py-4 text-sm font-medium text-forge-ink-900 dark:text-forge-ash-50"
                >
                  {model.name}
                </td>
                <td
                  class="px-6 py-4 text-sm text-forge-ash-600 dark:text-forge-ash-400"
                >
                  {model.provider}
                </td>
                <td
                  class="px-6 py-4 text-sm font-medium text-forge-brass-600 dark:text-forge-brass-400"
                >
                  {model.health.latencyMs}ms
                </td>
                <td class="px-6 py-4 text-sm">
                  <span
                    class="inline-flex rounded-full bg-forge-brass-100 px-3 py-1 text-xs font-medium text-forge-brass-800 dark:bg-forge-brass-900 dark:text-forge-brass-200"
                  >
                    {model.health.status}
                  </span>
                </td>
                <td class="px-6 py-4 text-sm">
                  <span
                    class="inline-flex rounded-full bg-forge-brass-100 px-3 py-1 text-xs font-medium text-forge-brass-800 dark:bg-forge-brass-900 dark:text-forge-brass-200"
                  >
                    Active
                  </span>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {:else}
      <p class="mt-4 text-forge-ash-600 dark:text-forge-ash-400">
        No models available
      </p>
    {/if}
  </div>
</div>

<style>
</style>
