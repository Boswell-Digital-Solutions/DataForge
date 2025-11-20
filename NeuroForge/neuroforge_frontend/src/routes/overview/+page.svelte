<script lang="ts">
  import { onMount } from 'svelte';
  import { setLoading } from '$lib/stores';
  import SystemHealthRow from '$lib/components/overview/SystemHealthRow.svelte';
  import PipelineSummaryCard from '$lib/components/overview/PipelineSummaryCard.svelte';
  import ModelStatusGrid from '$lib/components/overview/ModelStatusGrid.svelte';
  import RecentActivityList from '$lib/components/overview/RecentActivityList.svelte';
  import DomainSummaryPanel from '$lib/components/overview/DomainSummaryPanel.svelte';
  import EvaluationHighlights from '$lib/components/overview/EvaluationHighlights.svelte';
  import { fetchCompleteOverview } from '$lib/api/overviewApi';
  import type { OverviewData } from '$lib/types/overview';

  let overview: OverviewData | null = null;
  let loading = true;
  let error: string | null = null;

  onMount(async () => {
    try {
      setLoading(true);
      const response = await fetchCompleteOverview();

      if (response.success && response.data) {
        overview = response.data;
        error = null;
      } else {
        error = response.error?.message || 'Failed to load overview data';
        overview = null;
      }
    } catch (err: any) {
      error = err.message || 'An error occurred while fetching overview data';
      overview = null;
    } finally {
      loading = false;
      setLoading(false);
    }
  });

  function getActionButtonColor(color?: string): string {
    switch (color) {
      case 'primary':
        return 'bg-nf-ember-core hover:bg-nf-ember-core/90 text-white';
      case 'secondary':
        return 'bg-nf-pulse-violet hover:bg-nf-pulse-violet/90 text-white';
      case 'success':
        return 'bg-green-600 hover:bg-green-700 text-white';
      case 'warning':
        return 'bg-yellow-600 hover:bg-yellow-700 text-white';
      case 'danger':
        return 'bg-red-600 hover:bg-red-700 text-white';
      default:
        return 'bg-forge-ash-800 hover:bg-forge-ash-700 text-forge-ink-50';
    }
  }
</script>

<div class="space-y-8 pb-8">
  <!-- Page Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-4xl font-bold text-forge-ink-50">NeuroForge Overview</h1>
      <p class="text-forge-ink-dim mt-2">Real-time dashboard for LLM orchestration and model management</p>
    </div>
    <div class="text-right">
      <p class="text-sm text-forge-ink-dim">Last updated</p>
      <p class="text-lg font-semibold text-nf-neural-blue">
        {overview ? new Date(overview.timestamp).toLocaleTimeString() : '—'}
      </p>
    </div>
  </div>

  {#if loading}
    <!-- Loading State -->
    <div class="space-y-4">
      <div class="bg-forge-ash-900 border border-forge-ash-700 rounded-lg p-6 h-32 animate-pulse" />
      <div class="bg-forge-ash-900 border border-forge-ash-700 rounded-lg p-6 h-32 animate-pulse" />
    </div>
  {:else if error}
    <!-- Error State -->
    <div class="bg-red-900/20 border border-red-600/50 rounded-lg p-6">
      <p class="text-red-400 font-semibold mb-2">Failed to Load Overview</p>
      <p class="text-red-300/80 text-sm">{error}</p>
    </div>
  {:else if overview}
    <!-- 1. System Health Metrics -->
    <section class="space-y-3">
      <h2 class="text-2xl font-bold text-forge-ink-50">System Health</h2>
      <SystemHealthRow metrics={overview.systemHealth.metrics} />
    </section>

    <!-- 2. Active Pipelines -->
    <section class="space-y-3">
      <h2 class="text-2xl font-bold text-forge-ink-50">Active Pipelines</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        {#each overview.pipelines as pipeline (pipeline.id)}
          <PipelineSummaryCard {pipeline} />
        {/each}
      </div>
    </section>

    <!-- 3. Model Status Grid -->
    <section class="space-y-3">
      <h2 class="text-2xl font-bold text-forge-ink-50">Model Performance</h2>
      <ModelStatusGrid models={overview.models} />
    </section>

    <!-- 4. Recent Activity Stream -->
    <section class="space-y-3">
      <h2 class="text-2xl font-bold text-forge-ink-50">Recent Activity</h2>
      <RecentActivityList activities={overview.activity} />
    </section>

    <!-- 5. Domain Adapters -->
    <section class="space-y-3">
      <h2 class="text-2xl font-bold text-forge-ink-50">Domain Status</h2>
      <DomainSummaryPanel domains={overview.domains} />
    </section>

    <!-- 6. Evaluation Highlights -->
    <section class="space-y-3">
      <h2 class="text-2xl font-bold text-forge-ink-50">Model Evaluation</h2>
      <EvaluationHighlights evaluationData={overview.evaluationHighlights} />
    </section>

    <!-- 7. Quick Actions -->
    <section class="space-y-3">
      <h2 class="text-2xl font-bold text-forge-ink-50">Quick Actions</h2>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        {#each overview.quickActions as action (action.id)}
          <a href={action.href} class="block">
            <button
              class="w-full py-3 px-4 rounded-lg font-semibold transition-all duration-200 {getActionButtonColor(action.color)}"
              title={action.description}
            >
              <span class="mr-2">{action.icon}</span>
              {action.label}
            </button>
          </a>
        {/each}
      </div>
    </section>
  {:else}
    <!-- Empty State -->
    <div class="bg-forge-ash-900 border border-forge-ash-700 rounded-lg p-12 text-center">
      <p class="text-forge-ink-dim text-lg">No overview data available</p>
    </div>
  {/if}
</div>
