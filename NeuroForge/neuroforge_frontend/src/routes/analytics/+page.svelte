<script lang="ts">
  import { neuroforgeApi } from "$lib/api/neuroforge";
  import StatCard from "$lib/components/StatCard.svelte";
  import { onMount } from "svelte";
  import type { LogEntry } from "$lib/types";

  let logs: LogEntry[] = [];
  let loading = true;
  let error: string | null = null;
  let filteredDomain = "all";
  let dateFrom = "";
  let dateTo = "";

  onMount(async () => {
    try {
      const response = await neuroforgeApi.fetchLogs(undefined, undefined, 100);
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

  $: filteredLogs = logs
    .filter((l) =>
      filteredDomain === "all" ? true : l.domain === filteredDomain
    )
    .filter((l) => {
      let matchesDate = true;
      if (dateFrom) {
        matchesDate =
          new Date(l.created_at).getTime() >= new Date(dateFrom).getTime();
      }
      if (dateTo && matchesDate) {
        matchesDate =
          new Date(l.created_at).getTime() <= new Date(dateTo).getTime();
      }
      return matchesDate;
    });

  $: domains = Array.from(new Set(logs.map((l) => l.domain)));

  // Calculate metrics
  $: avgScore =
    filteredLogs.length > 0
      ? (
          filteredLogs.reduce((sum, l) => sum + (l.evaluation_score ?? 0), 0) /
          filteredLogs.length
        ).toFixed(1)
      : "0";

  $: avgLatency =
    filteredLogs.length > 0
      ? (
          filteredLogs.reduce((sum, l) => sum + (l.latency_ms ?? 0), 0) /
          filteredLogs.length
        ).toFixed(0)
      : "0";

  $: successRate =
    filteredLogs.length > 0
      ? (
          (filteredLogs.filter((l) => (l.evaluation_score ?? 0) > 0.7).length /
            filteredLogs.length) *
          100
        ).toFixed(1)
      : "0";

  $: totalRequests = filteredLogs.length;
</script>

<div class="space-y-8">
  <div>
    <h1 class="text-3xl font-bold text-forge-ink-900 dark:text-forge-ash-50">
      Analytics
    </h1>
    <p class="mt-2 text-forge-ash-600 dark:text-forge-ash-400">
      View inference logs and performance metrics
    </p>
  </div>

  {#if error}
    <div
      class="rounded-lg border border-forge-ember-200 bg-forge-ember-50 p-4 dark:border-forge-ember-800 dark:bg-forge-ember-950"
    >
      <p class="text-forge-ember-800 dark:text-forge-ember-200">{error}</p>
    </div>
  {/if}

  {#if !loading && filteredLogs.length > 0}
    <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
      <StatCard title="Total Requests" value={totalRequests.toString()} />
      <StatCard title="Avg Quality Score" value={`${avgScore}%`} />
      <StatCard title="Avg Latency" value={`${avgLatency}ms`} />
      <StatCard title="Success Rate" value={`${successRate}%`} />
    </div>
  {/if}

  <div
    class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-6 dark:border-forge-ash-700 dark:bg-forge-ash-900"
  >
    <h2 class="text-lg font-semibold text-forge-ink-900 dark:text-forge-ash-50">
      Filters
    </h2>

    <div class="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
      <div>
        <label
          class="block text-sm font-medium text-forge-ink-900 dark:text-forge-ash-50"
          >Domain</label
        >
        <select
          bind:value={filteredDomain}
          class="mt-2 w-full rounded-lg border border-forge-ash-300 bg-forge-ash-50 px-4 py-2 text-forge-ink-900 dark:border-forge-ash-600 dark:bg-forge-ash-800 dark:text-forge-ash-50"
        >
          <option value="all">All Domains</option>
          {#each domains as domain}
            <option value={domain}>{domain}</option>
          {/each}
        </select>
      </div>

      <div>
        <label
          class="block text-sm font-medium text-forge-ink-900 dark:text-forge-ash-50"
          >From Date</label
        >
        <input
          type="date"
          bind:value={dateFrom}
          class="mt-2 w-full rounded-lg border border-forge-ash-300 bg-forge-ash-50 px-4 py-2 text-forge-ink-900 dark:border-forge-ash-600 dark:bg-forge-ash-800 dark:text-forge-ash-50"
        />
      </div>

      <div>
        <label
          class="block text-sm font-medium text-forge-ink-900 dark:text-forge-ash-50"
          >To Date</label
        >
        <input
          type="date"
          bind:value={dateTo}
          class="mt-2 w-full rounded-lg border border-forge-ash-300 bg-forge-ash-50 px-4 py-2 text-forge-ink-900 dark:border-forge-ash-600 dark:bg-forge-ash-800 dark:text-forge-ash-50"
        />
      </div>
    </div>
  </div>

  {#if loading}
    <div class="space-y-3">
      {#each { length: 5 } as _}
        <div
          class="h-16 animate-pulse rounded-lg bg-forge-ash-200 dark:bg-forge-ash-700"
        />
      {/each}
    </div>
  {:else if filteredLogs.length > 0}
    <div
      class="overflow-x-auto rounded-lg border border-forge-ash-200 dark:border-forge-ash-700"
    >
      <table class="w-full">
        <thead
          class="border-b border-forge-ash-200 bg-forge-ash-50 dark:border-forge-ash-700 dark:bg-forge-ash-900"
        >
          <tr>
            <th
              class="px-6 py-4 text-left text-sm font-semibold text-forge-ink-900 dark:text-forge-ash-50"
            >
              Timestamp
            </th>
            <th
              class="px-6 py-4 text-left text-sm font-semibold text-forge-ink-900 dark:text-forge-ash-50"
            >
              Domain
            </th>
            <th
              class="px-6 py-4 text-left text-sm font-semibold text-forge-ink-900 dark:text-forge-ash-50"
            >
              Task
            </th>
            <th
              class="px-6 py-4 text-left text-sm font-semibold text-forge-ink-900 dark:text-forge-ash-50"
            >
              Model
            </th>
            <th
              class="px-6 py-4 text-left text-sm font-semibold text-forge-ink-900 dark:text-forge-ash-50"
            >
              Score
            </th>
            <th
              class="px-6 py-4 text-left text-sm font-semibold text-forge-ink-900 dark:text-forge-ash-50"
            >
              Latency
            </th>
          </tr>
        </thead>
        <tbody>
          {#each filteredLogs as log}
            <tr
              class="border-b border-forge-ash-100 hover:bg-forge-ash-50 dark:border-forge-ash-800 dark:hover:bg-forge-ash-800"
            >
              <td
                class="px-6 py-4 text-sm text-forge-ash-600 dark:text-forge-ash-400"
              >
                {new Date(log.created_at).toLocaleString()}
              </td>
              <td
                class="px-6 py-4 text-sm font-medium text-forge-ink-900 dark:text-forge-ash-50"
              >
                {log.domain}
              </td>
              <td
                class="px-6 py-4 text-sm text-forge-ash-600 dark:text-forge-ash-400"
              >
                {log.task_type}
              </td>
              <td
                class="px-6 py-4 text-sm text-forge-ash-600 dark:text-forge-ash-400"
              >
                {log.model_id}
              </td>
              <td
                class="px-6 py-4 text-sm font-medium text-forge-brass-600 dark:text-forge-brass-400"
              >
                {((log.evaluation_score ?? 0) * 100).toFixed(1)}%
              </td>
              <td
                class="px-6 py-4 text-sm text-forge-ash-600 dark:text-forge-ash-400"
              >
                {log.latency_ms ?? "N/A"}ms
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {:else}
    <p class="text-forge-ash-600 dark:text-forge-ash-400">No logs available</p>
  {/if}
</div>

<style>
</style>
