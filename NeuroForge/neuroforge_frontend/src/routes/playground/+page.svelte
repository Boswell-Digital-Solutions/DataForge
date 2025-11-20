<script lang="ts">
  import { neuroforgeApi } from "$lib/api/neuroforge";
  import Button from "$lib/components/Button.svelte";
  import Alert from "$lib/components/Alert.svelte";
  import { onMount } from "svelte";
  import type { InferenceRequest, InferenceResult } from "$lib/types";

  let domain = "literary";
  let taskType = "analysis";
  let prompt = "";
  let loading = false;
  let result: InferenceResult | null = null;
  let error: string | null = null;
  let successMessage: string | null = null;

  const domains = ["literary", "market", "general"];
  const taskTypes = ["analysis", "generation", "reasoning"];

  async function submitInference() {
    if (!prompt.trim()) {
      error = "Please enter a prompt";
      return;
    }

    error = null;
    successMessage = null;
    loading = true;

    try {
      const request: InferenceRequest = {
        domain: domain as any,
        taskType: taskType as any,
        contextPackId: `pack-${Date.now()}`,
        userQuery: prompt,
        maxTokens: 1000,
      };

      const response = await neuroforgeApi.runInference(request);
      if (response.success && response.data) {
        result = response.data;
        const score = result.evaluation?.scores?.[0]?.score ?? 0;
        successMessage = `Inference completed in ${
          result.latencyMs
        }ms with score ${(score * 100).toFixed(1)}%`;
      } else {
        error = response.error?.message || "Failed to submit inference";
      }
    } catch (err: any) {
      error = err.message || "An error occurred";
    } finally {
      loading = false;
    }
  }

  function clearResult() {
    result = null;
    prompt = "";
    domain = "literary";
    taskType = "analysis";
  }
</script>

<div class="space-y-8">
  <div>
    <h1 class="text-3xl font-bold text-forge-ink-900 dark:text-forge-ash-50">
      Inference Playground
    </h1>
    <p class="mt-2 text-forge-ash-600 dark:text-forge-ash-400">
      Test the NeuroForge pipeline with your own prompts
    </p>
  </div>

  {#if error}
    <Alert
      type="error"
      message={error}
      onDismiss={() => {
        error = null;
      }}
    />
  {/if}

  {#if successMessage}
    <Alert
      type="success"
      message={successMessage}
      onDismiss={() => {
        successMessage = null;
      }}
    />
  {/if}

  <div class="grid grid-cols-3 gap-8">
    <!-- Input Panel -->
    <div class="col-span-2 space-y-6">
      <div
        class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-6 dark:border-forge-ash-700 dark:bg-forge-ash-900"
      >
        <h2
          class="text-lg font-semibold text-forge-ink-900 dark:text-forge-ash-50"
        >
          Configuration
        </h2>

        <div class="mt-6 space-y-4">
          <!-- Domain Selection -->
          <div>
            <label
              class="block text-sm font-medium text-forge-ink-900 dark:text-forge-ash-50"
              for="domain-select">Domain</label
            >
            <select
              id="domain-select"
              bind:value={domain}
              disabled={loading}
              class="mt-2 w-full rounded-lg border border-forge-ash-300 bg-forge-ash-50 px-4 py-2 text-forge-ink-900 dark:border-forge-ash-600 dark:bg-forge-ash-800 dark:text-forge-ash-50 disabled:opacity-50"
            >
              {#each domains as d}
                <option value={d}
                  >{d.charAt(0).toUpperCase() + d.slice(1)}</option
                >
              {/each}
            </select>
          </div>

          <!-- Task Type Selection -->
          <div>
            <label
              class="block text-sm font-medium text-forge-ink-900 dark:text-forge-ash-50"
              for="tasktype-select">Task Type</label
            >
            <select
              id="tasktype-select"
              bind:value={taskType}
              disabled={loading}
              class="mt-2 w-full rounded-lg border border-forge-ash-300 bg-forge-ash-50 px-4 py-2 text-forge-ink-900 dark:border-forge-ash-600 dark:bg-forge-ash-800 dark:text-forge-ash-50 disabled:opacity-50"
            >
              {#each taskTypes as t}
                <option value={t}
                  >{t.charAt(0).toUpperCase() + t.slice(1)}</option
                >
              {/each}
            </select>
          </div>

          <!-- Prompt Input -->
          <div>
            <label
              class="block text-sm font-medium text-forge-ink-900 dark:text-forge-ash-50"
              for="prompt-input">Prompt</label
            >
            <textarea
              id="prompt-input"
              bind:value={prompt}
              disabled={loading}
              placeholder="Enter your prompt here..."
              class="mt-2 h-48 w-full rounded-lg border border-forge-ash-300 bg-forge-ash-50 px-4 py-2 text-forge-ink-900 placeholder-forge-ash-500 dark:border-forge-ash-600 dark:bg-forge-ash-800 dark:text-forge-ash-50 dark:placeholder-forge-ash-400 disabled:opacity-50"
            />
          </div>
        </div>

        <div class="mt-6 flex space-x-3">
          <Button
            variant="primary"
            onClick={submitInference}
            {loading}
            disabled={!prompt.trim() || loading}
          >
            Submit Inference
          </Button>
          {#if result}
            <Button
              variant="secondary"
              onClick={clearResult}
              disabled={loading}
            >
              Clear Result
            </Button>
          {/if}
        </div>
      </div>
    </div>

    <!-- Results Panel -->
    <div class="space-y-6">
      {#if loading}
        <div
          class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-6 dark:border-forge-ash-700 dark:bg-forge-ash-900"
        >
          <div class="space-y-3">
            <div
              class="h-4 w-3/4 animate-pulse rounded bg-forge-ash-300 dark:bg-forge-ash-600"
            />
            <div
              class="h-4 w-full animate-pulse rounded bg-forge-ash-300 dark:bg-forge-ash-600"
            />
            <div
              class="h-4 w-5/6 animate-pulse rounded bg-forge-ash-300 dark:bg-forge-ash-600"
            />
          </div>
        </div>
      {:else if result}
        <div
          class="rounded-lg border border-forge-ash-200 bg-forge-ash-50 p-6 dark:border-forge-ash-700 dark:bg-forge-ash-900"
        >
          <h2
            class="text-lg font-semibold text-forge-ink-900 dark:text-forge-ash-50"
          >
            Result
          </h2>

          <div class="mt-4 space-y-4">
            <!-- Output -->
            <div>
              <h3
                class="text-sm font-medium text-forge-ash-600 dark:text-forge-ash-400"
              >
                Output
              </h3>
              <p
                class="mt-2 whitespace-pre-wrap rounded bg-forge-ash-50 p-3 text-sm dark:bg-forge-ash-800"
              >
                {result.output}
              </p>
            </div>

            <!-- Metrics -->
            <div
              class="space-y-2 border-t border-forge-ash-200 pt-4 dark:border-forge-ash-700"
            >
              <div class="flex justify-between">
                <span class="text-sm text-forge-ash-600 dark:text-forge-ash-400"
                  >Score</span
                >
                <span
                  class="font-semibold text-forge-ink-900 dark:text-forge-ash-50"
                >
                  {((result.evaluation?.scores?.[0]?.score ?? 0) * 100).toFixed(
                    1
                  )}%
                </span>
              </div>
              <div class="flex justify-between">
                <span class="text-sm text-forge-ash-600 dark:text-forge-ash-400"
                  >Latency</span
                >
                <span
                  class="font-semibold text-forge-ink-900 dark:text-forge-ash-50"
                >
                  {result.latencyMs}ms
                </span>
              </div>
              <div class="flex justify-between">
                <span class="text-sm text-forge-ash-600 dark:text-forge-ash-400"
                  >Model</span
                >
                <span
                  class="font-semibold text-forge-ink-900 dark:text-forge-ash-50"
                >
                  {result.modelId}
                </span>
              </div>
            </div>
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
</style>
