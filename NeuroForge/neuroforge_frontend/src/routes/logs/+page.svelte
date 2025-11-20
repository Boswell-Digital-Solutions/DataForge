<script lang="ts">
  import { neuroforgeApi } from "$lib/api/neuroforge";
  import { onMount } from "svelte";
  import type { LogEntry } from "$lib/types";

  let logs: LogEntry[] = [];
  let loading = true;
  let error: string | null = null;
  let searchTerm = "";
  let selectedDomain = "";
  let selectedTaskType = "";
  let dateFrom = "";
  let dateTo = "";

  onMount(async () => {
    try {
      const response = await neuroforgeApi.fetchLogs(undefined, undefined, 200);
      if (response.success && response.data) {
        logs = response.data;
      } else {
        error = response.error?.message || "Failed to load logs";
      }
    } catch (err: any) {
      error = err.message || "An error occurred";
    } finally {
      loading = false;
    }
  });

  // Get unique domains and task types from logs
  $: domains = [...new Set(logs.map((l) => l.domain).filter(Boolean))].sort();
  $: taskTypes = [
    ...new Set(logs.map((l) => l.task_type).filter(Boolean)),
  ].sort();

  $: filteredLogs = logs.filter((log) => {
    const matchesSearch =
      !searchTerm ||
      log.model_id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.domain?.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesDomain = !selectedDomain || log.domain === selectedDomain;
    const matchesTaskType =
      !selectedTaskType || log.task_type === selectedTaskType;

    let matchesDateRange = true;
    if (dateFrom || dateTo) {
      const logDate = new Date(log.created_at).getTime();
      if (dateFrom) {
        matchesDateRange = logDate >= new Date(dateFrom).getTime();
      }
      if (dateTo && matchesDateRange) {
        matchesDateRange = logDate <= new Date(dateTo).getTime();
      }
    }

    return (
      matchesSearch && matchesDomain && matchesTaskType && matchesDateRange
    );
  });
</script>

<div class="space-y-8">
  <div>
    <h1 class="text-3xl font-bold text-forge-ink-900 dark:text-forge-ash-50">
      Inference Logs
    </h1>
    <p class="mt-2 text-forge-ash-600 dark:text-forge-ash-400">
      Complete history of all inference requests
    </p>
  </div>

  {#if error}
    <div
      class="rounded-lg border border-forge-ember-200 bg-forge-ember-50 p-4 dark:border-forge-ember-800 dark:bg-forge-ember-950"
    >
      <p class="text-forge-ember-800 dark:text-forge-ember-200">{error}</p>
    </div>
  {/if}

  <div
    class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-6 dark:border-forge-ash-700 dark:bg-forge-ash-900"
  >
    <div class="space-y-4">
      <!-- Search Bar -->
      <input
        type="text"
        placeholder="Search by model ID or domain..."
        bind:value={searchTerm}
        class="w-full rounded-lg border border-forge-ash-300 bg-forge-ash-50 px-4 py-2 text-forge-ink-900 placeholder-forge-ash-500 dark:border-forge-ash-600 dark:bg-forge-ash-800 dark:text-forge-ash-50 dark:placeholder-forge-ash-400"
      />

      <!-- Filters Row -->
      <div class="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
        <select
          bind:value={selectedDomain}
          class="rounded-lg border border-forge-ash-300 bg-forge-ash-50 px-3 py-2 text-sm text-forge-ink-900 dark:border-forge-ash-600 dark:bg-forge-ash-800 dark:text-forge-ash-50"
        >
          <option value="">All Domains</option>
          {#each domains as domain}
            <option value={domain}>{domain}</option>
          {/each}
        </select>

        <select
          bind:value={selectedTaskType}
          class="rounded-lg border border-forge-ash-300 bg-forge-ash-50 px-3 py-2 text-sm text-forge-ink-900 dark:border-forge-ash-600 dark:bg-forge-ash-800 dark:text-forge-ash-50"
        >
          <option value="">All Task Types</option>
          {#each taskTypes as taskType}
            <option value={taskType}>{taskType}</option>
          {/each}
        </select>

        <input
          type="date"
          bind:value={dateFrom}
          class="rounded-lg border border-forge-ash-300 bg-forge-ash-50 px-3 py-2 text-sm text-forge-ink-900 dark:border-forge-ash-600 dark:bg-forge-ash-800 dark:text-forge-ash-50"
          placeholder="From date"
        />

        <input
          type="date"
          bind:value={dateTo}
          class="rounded-lg border border-forge-ash-300 bg-forge-ash-50 px-3 py-2 text-sm text-forge-ink-900 dark:border-forge-ash-600 dark:bg-forge-ash-800 dark:text-forge-ash-50"
          placeholder="To date"
        />
      </div>
    </div>

    <p class="mt-4 text-xs text-forge-ash-600 dark:text-forge-ash-400">
      Showing {filteredLogs.length} of {logs.length} logs
    </p>
  </div>

  {#if loading}
    <div class="space-y-3">
      {#each { length: 10 } as _}
        <div
          class="h-12 animate-pulse rounded-lg bg-forge-ash-200 dark:bg-forge-ash-700"
        />
      {/each}
    </div>
  {:else if filteredLogs.length > 0}
    <div class="space-y-3">
      {#each filteredLogs as log}
        <div
          class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-4 hover:shadow-md dark:border-forge-ash-700 dark:bg-forge-ash-900"
        >
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <div class="flex items-center space-x-4">
                <div>
                  <p
                    class="font-semibold text-forge-ink-900 dark:text-forge-ash-50"
                  >
                    {log.model_id}
                  </p>
                  <p class="text-xs text-forge-ash-600 dark:text-forge-ash-400">
                    {new Date(log.created_at).toLocaleString()}
                  </p>
                </div>
                <div class="hidden sm:block">
                  <span
                    class="inline-block rounded-full bg-forge-ash-100 px-3 py-1 text-xs font-medium text-forge-ink-900 dark:bg-forge-ash-800 dark:text-forge-ash-50"
                  >
                    {log.domain}
                  </span>
                  <span
                    class="ml-2 inline-block rounded-full bg-forge-brass-100 px-3 py-1 text-xs font-medium text-forge-brass-800 dark:bg-forge-brass-900 dark:text-forge-brass-200"
                  >
                    {log.task_type}
                  </span>
                </div>
              </div>
            </div>
            <div class="flex flex-col items-end space-y-1">
              <p
                class="font-bold text-forge-brass-600 dark:text-forge-brass-400"
              >
                {((log.evaluation_score ?? 0) * 100).toFixed(1)}%
              </p>
              <p class="text-xs text-forge-ash-600 dark:text-forge-ash-400">
                {log.latency_ms ?? "N/A"}ms
              </p>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {:else}
    <p class="text-center text-forge-ash-600 dark:text-forge-ash-400">
      No logs found
    </p>
  {/if}
</div>

<style>
</style>
