<script lang="ts">
  import type { PipelineSummary } from '$lib/types/overview';
  import { Domain } from '$lib/types';

  export let pipeline: PipelineSummary;

  function getDomainLabel(domain: string): string {
    const labels = {
      [Domain.LITERARY]: '📚 Literary',
      [Domain.MARKET]: '📈 Market',
      [Domain.GENERAL]: '🧠 General',
    };
    return labels[domain] || domain;
  }

  function getStatusColor(status: string): string {
    switch (status) {
      case 'active':
        return 'bg-green-500/20 border-green-500/50 text-green-400';
      case 'inactive':
        return 'bg-gray-500/20 border-gray-500/50 text-gray-400';
      case 'paused':
        return 'bg-yellow-500/20 border-yellow-500/50 text-yellow-400';
      default:
        return 'bg-forge-ash-800 border-forge-ash-700 text-forge-ink-400';
    }
  }

  function getSuccessRateColor(rate: number): string {
    if (rate >= 0.99) return 'text-green-400';
    if (rate >= 0.95) return 'text-yellow-400';
    return 'text-red-400';
  }
</script>

<div class="bg-forge-ash-900 border border-forge-ash-700 rounded-lg p-6 hover:border-nf-pulse-violet transition-colors">
  <div class="flex items-start justify-between mb-4">
    <div>
      <h3 class="text-lg font-semibold text-forge-ink-50">{getDomainLabel(pipeline.domain)}</h3>
      <p class="text-sm text-forge-ink-dim mt-1">Pipeline Status</p>
    </div>
    <div class="px-3 py-1 rounded border {getStatusColor(pipeline.status)}">
      <span class="text-xs font-semibold capitalize">{pipeline.status}</span>
    </div>
  </div>

  <div class="space-y-3">
    <div class="flex justify-between items-center text-sm">
      <span class="text-forge-ink-dim">Active Models</span>
      <span class="text-forge-ink-50 font-semibold">
        {pipeline.activeModels}/{pipeline.totalModels}
      </span>
    </div>

    <div class="flex justify-between items-center text-sm">
      <span class="text-forge-ink-dim">Requests (24h)</span>
      <span class="text-forge-ink-50 font-semibold">{pipeline.requestsLast24h.toLocaleString()}</span>
    </div>

    <div class="flex justify-between items-center text-sm">
      <span class="text-forge-ink-dim">Avg Latency</span>
      <span class="text-forge-ink-50 font-semibold">{pipeline.averageLatencyMs}ms</span>
    </div>

    <div class="flex justify-between items-center text-sm">
      <span class="text-forge-ink-dim">Success Rate</span>
      <span class={getSuccessRateColor(pipeline.successRate)}>
        {(pipeline.successRate * 100).toFixed(1)}%
      </span>
    </div>

    <div class="flex justify-between items-center text-sm">
      <span class="text-forge-ink-dim">Errors (24h)</span>
      <span class="text-red-400 font-semibold">{pipeline.errorCount}</span>
    </div>
  </div>

  <div class="mt-4 pt-4 border-t border-forge-ash-700">
    <p class="text-xs text-forge-ink-dim">
      Last request: {pipeline.lastRequest ? new Date(pipeline.lastRequest).toLocaleTimeString() : 'Never'}
    </p>
  </div>
</div>
