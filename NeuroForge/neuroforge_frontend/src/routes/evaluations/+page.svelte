<script lang="ts">
  import { neuroforgeApi } from "$lib/api/neuroforge";
  import { onMount } from "svelte";
  import type { EvaluationRun, InferenceResult } from "$lib/types";
  import Button from "$lib/components/Button.svelte";
  import Alert from "$lib/components/Alert.svelte";

  let evaluations: EvaluationRun[] = [];
  let selectedEvaluation: EvaluationRun | null = null;
  let selectedCompare: InferenceResult[] = [];
  let loading = true;
  let error: string | null = null;
  let successMessage: string | null = null;
  let sortColumn: keyof EvaluationRun = "createdAt";
  let sortAsc = false;

  onMount(async () => {
    await loadEvaluations();
  });

  async function loadEvaluations() {
    try {
      loading = true;
      error = null;
      const response = await neuroforgeApi.fetchEvaluationRuns();
      if (response.success && response.data) {
        evaluations = response.data;
      } else {
        error = response.error?.message || "Failed to load evaluations";
      }
    } catch (err: any) {
      error = err.message || "An error occurred";
    } finally {
      loading = false;
    }
  }

  function sortBy(column: keyof EvaluationRun) {
    if (sortColumn === column) {
      sortAsc = !sortAsc;
    } else {
      sortColumn = column;
      sortAsc = true;
    }
  }

  $: sortedEvaluations = [...evaluations].sort((a, b) => {
    const aVal = a[sortColumn];
    const bVal = b[sortColumn];
    if (aVal === undefined || bVal === undefined) return 0;
    const cmp = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
    return sortAsc ? cmp : -cmp;
  });

  function toggleCompare(result: InferenceResult) {
    const idx = selectedCompare.findIndex(
      (r) => r.inferenceId === result.inferenceId
    );
    if (idx >= 0) {
      selectedCompare = selectedCompare.filter((_, i) => i !== idx);
    } else if (selectedCompare.length < 3) {
      selectedCompare = [...selectedCompare, result];
    }
  }

  function clearMessages() {
    error = null;
    successMessage = null;
  }

  function formatDate(date: string): string {
    return new Date(date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function getScoreColor(score: number): string {
    if (score >= 0.85) return "text-forge-brass-600 dark:text-forge-brass-400";
    if (score >= 0.7) return "text-forge-ember-600 dark:text-forge-ember-400";
    return "text-forge-ash-600 dark:text-forge-ash-400";
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div>
    <h1 class="text-3xl font-bold text-forge-ink-900 dark:text-forge-ash-50">
      Evaluations & Experiments
    </h1>
    <p class="mt-1 text-forge-ash-600 dark:text-forge-ash-400">
      Review evaluation runs and compare model outputs
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
  <div class="grid grid-cols-3 gap-6">
    <!-- Evaluation Runs List -->
    <div class="col-span-2 space-y-4">
      {#if loading}
        <div
          class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-6 dark:border-forge-ash-700 dark:bg-forge-ash-900"
        >
          <div class="space-y-3">
            {#each [1, 2, 3] as _}
              <div
                class="h-20 animate-pulse rounded bg-forge-ash-200 dark:bg-forge-ash-700"
              />
            {/each}
          </div>
        </div>
      {:else if evaluations.length === 0}
        <div
          class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-12 text-center dark:border-forge-ash-700 dark:bg-forge-ash-900"
        >
          <p class="text-forge-ash-600 dark:text-forge-ash-400">
            No evaluation runs yet
          </p>
        </div>
      {:else}
        <div class="space-y-3">
          {#each sortedEvaluations as evaluation (evaluation.id)}
            <div
              on:click={() => (selectedEvaluation = evaluation)}
              class={`cursor-pointer rounded-lg border p-4 transition ${
                selectedEvaluation?.id === evaluation.id
                  ? "border-forge-ember-600 bg-forge-ember-50 dark:border-forge-ember-600 dark:bg-forge-ash-800"
                  : "border-forge-ash-200 bg-forge-ash-50 hover:border-forge-ash-300 dark:border-forge-ash-700 dark:bg-forge-ash-900 dark:hover:border-forge-ash-600"
              }`}
            >
              <div class="flex items-start justify-between">
                <div class="flex-1">
                  <h3
                    class="font-semibold text-forge-ink-900 dark:text-forge-ash-50"
                  >
                    {evaluation.domain} · {evaluation.pipelineId}
                  </h3>
                  <p
                    class="mt-1 text-sm text-forge-ash-600 dark:text-forge-ash-400"
                  >
                    {formatDate(evaluation.createdAt)} · {evaluation
                      .modelsTested.length} models tested
                  </p>
                  <div class="mt-2 flex gap-2">
                    {#each evaluation.modelsTested.slice(0, 3) as model}
                      <span
                        class="rounded bg-forge-brass-100 px-2 py-1 text-xs font-medium text-forge-brass-800 dark:bg-forge-brass-900 dark:text-forge-brass-200"
                      >
                        {model}
                      </span>
                    {/each}
                    {#if evaluation.modelsTested.length > 3}
                      <span
                        class="rounded bg-forge-ash-100 px-2 py-1 text-xs font-medium text-forge-ash-800 dark:bg-forge-ash-700 dark:text-forge-ash-200"
                      >
                        +{evaluation.modelsTested.length - 3}
                      </span>
                    {/if}
                  </div>
                </div>
                <div class="text-right">
                  <div
                    class={`text-lg font-bold ${getScoreColor(
                      evaluation.summary.averageQualityScore
                    )}`}
                  >
                    {(evaluation.summary.averageQualityScore * 100).toFixed(0)}%
                  </div>
                  <p class="text-xs text-forge-ash-600 dark:text-forge-ash-400">
                    avg score
                  </p>
                </div>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>

    <!-- Detail Panel & Comparison -->
    <div class="col-span-1 space-y-4">
      {#if selectedEvaluation}
        <div
          class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-6 dark:border-forge-ash-700 dark:bg-forge-ash-900"
        >
          <div class="flex items-start justify-between">
            <h3
              class="text-lg font-semibold text-forge-ink-900 dark:text-forge-ash-50"
            >
              Run Details
            </h3>
            <button
              on:click={() => (selectedEvaluation = null)}
              class="text-forge-ash-600 hover:text-forge-ink-900 dark:text-forge-ash-400 dark:hover:text-forge-ash-50"
            >
              ✕
            </button>
          </div>

          <div
            class="mt-4 space-y-3 border-t border-forge-ash-200 pt-4 dark:border-forge-ash-700"
          >
            <!-- Summary Stats -->
            <div>
              <p
                class="text-xs font-medium text-forge-ash-600 dark:text-forge-ash-400"
              >
                Avg Quality Score
              </p>
              <p
                class="mt-1 text-xl font-bold text-forge-ember-600 dark:text-forge-ember-400"
              >
                {(selectedEvaluation.summary.averageQualityScore * 100).toFixed(
                  1
                )}%
              </p>
            </div>

            <div>
              <p
                class="text-xs font-medium text-forge-ash-600 dark:text-forge-ash-400"
              >
                Avg Latency
              </p>
              <p
                class="mt-1 font-semibold text-forge-ink-900 dark:text-forge-ash-50"
              >
                {selectedEvaluation.summary.averageLatencyMs.toFixed(0)}ms
              </p>
            </div>

            <div>
              <p
                class="text-xs font-medium text-forge-ash-600 dark:text-forge-ash-400"
              >
                Success Rate
              </p>
              <p
                class="mt-1 font-semibold text-forge-ink-900 dark:text-forge-ash-50"
              >
                {(selectedEvaluation.summary.successRate * 100).toFixed(1)}%
              </p>
            </div>

            <div>
              <p
                class="text-xs font-medium text-forge-ash-600 dark:text-forge-ash-400"
              >
                Total Cost
              </p>
              <p
                class="mt-1 font-semibold text-forge-ink-900 dark:text-forge-ash-50"
              >
                ${selectedEvaluation.summary.totalCost.toFixed(4)}
              </p>
            </div>

            <!-- Recommended Champion -->
            <div
              class="border-t border-forge-ash-200 pt-3 dark:border-forge-ash-700"
            >
              <p
                class="text-xs font-medium text-forge-ash-600 dark:text-forge-ash-400"
              >
                🏆 Recommended Champion
              </p>
              <p
                class="mt-1 rounded-lg bg-forge-brass-50 px-3 py-2 font-semibold text-forge-brass-800 dark:bg-forge-brass-900 dark:text-forge-brass-200"
              >
                {selectedEvaluation.summary.recommendedChampion}
              </p>
            </div>

            <!-- Models Tested -->
            <div
              class="border-t border-forge-ash-200 pt-3 dark:border-forge-ash-700"
            >
              <p
                class="text-xs font-medium text-forge-ash-600 dark:text-forge-ash-400"
              >
                Models Tested
              </p>
              <div class="mt-2 space-y-1">
                {#each selectedEvaluation.modelsTested as model}
                  <p class="text-sm text-forge-ink-900 dark:text-forge-ash-50">
                    • {model}
                  </p>
                {/each}
              </div>
            </div>
          </div>
        </div>

        <!-- Comparison View -->
        {#if selectedEvaluation.results.length > 0}
          <div
            class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-6 dark:border-forge-ash-700 dark:bg-forge-ash-900"
          >
            <h4
              class="text-sm font-semibold text-forge-ink-900 dark:text-forge-ash-50"
            >
              Compare Outputs
            </h4>
            <p class="mt-1 text-xs text-forge-ash-600 dark:text-forge-ash-400">
              Select up to 3 results
            </p>

            <div class="mt-3 space-y-2 max-h-64 overflow-y-auto">
              {#each selectedEvaluation.results as result (result.inferenceId)}
                <label
                  class="flex items-center gap-2 rounded-lg p-2 hover:bg-forge-ash-50 dark:hover:bg-forge-ash-800"
                >
                  <input
                    type="checkbox"
                    checked={selectedCompare.some(
                      (r) => r.inferenceId === result.inferenceId
                    )}
                    on:change={() => toggleCompare(result)}
                    class="h-4 w-4"
                  />
                  <span class="flex-1 text-sm">
                    <span class="font-medium">{result.modelId}</span>
                    <span
                      class="ml-1 text-xs text-forge-ash-600 dark:text-forge-ash-400"
                    >
                      {(
                        result.evaluation?.scores?.[0]?.score ?? 0 * 100
                      ).toFixed(0)}%
                    </span>
                  </span>
                </label>
              {/each}
            </div>
          </div>
        {/if}
      {:else}
        <div
          class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-6 text-center dark:border-forge-ash-700 dark:bg-forge-ash-900"
        >
          <p class="text-forge-ash-600 dark:text-forge-ash-400">
            Select an evaluation run to view details
          </p>
        </div>
      {/if}
    </div>
  </div>

  <!-- Comparison Panel -->
  {#if selectedCompare.length > 0}
    <div
      class="rounded-lg border border-forge-brass-200 bg-forge-brass-50 p-6 dark:border-forge-brass-700 dark:bg-forge-ash-800"
    >
      <div class="mb-4 flex items-center justify-between">
        <h3
          class="text-lg font-semibold text-forge-ink-900 dark:text-forge-ash-50"
        >
          Side-by-Side Comparison ({selectedCompare.length} results)
        </h3>
        <button
          on:click={() => (selectedCompare = [])}
          class="text-sm text-forge-ash-600 hover:text-forge-ink-900 dark:text-forge-ash-400 dark:hover:text-forge-ash-50"
        >
          Clear comparison
        </button>
      </div>

      <div
        class="grid gap-4"
        style={`grid-template-columns: repeat(${selectedCompare.length}, 1fr)`}
      >
        {#each selectedCompare as result (result.inferenceId)}
          <div
            class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-4 dark:border-forge-ash-700 dark:bg-forge-ash-900"
          >
            <div class="space-y-3">
              <div>
                <p
                  class="text-xs font-medium text-forge-ash-600 dark:text-forge-ash-400"
                >
                  Model
                </p>
                <p
                  class="mt-1 font-semibold text-forge-ink-900 dark:text-forge-ash-50"
                >
                  {result.modelId}
                </p>
              </div>

              <div>
                <p
                  class="text-xs font-medium text-forge-ash-600 dark:text-forge-ash-400"
                >
                  Output
                </p>
                <p
                  class="mt-1 line-clamp-6 whitespace-pre-wrap rounded bg-forge-ash-50 p-2 text-xs text-forge-ink-900 dark:bg-forge-ash-800 dark:text-forge-ash-50"
                >
                  {result.output}
                </p>
              </div>

              <div
                class="grid grid-cols-2 gap-2 border-t border-forge-ash-200 pt-3 dark:border-forge-ash-700"
              >
                <div>
                  <p class="text-xs text-forge-ash-600 dark:text-forge-ash-400">
                    Score
                  </p>
                  <p
                    class="font-bold text-forge-brass-600 dark:text-forge-brass-400"
                  >
                    {(
                      (result.evaluation?.scores?.[0]?.score ?? 0) * 100
                    ).toFixed(0)}%
                  </p>
                </div>
                <div>
                  <p class="text-xs text-forge-ash-600 dark:text-forge-ash-400">
                    Latency
                  </p>
                  <p
                    class="font-bold text-forge-ember-600 dark:text-forge-ember-400"
                  >
                    {result.latencyMs}ms
                  </p>
                </div>
              </div>
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
</style>
