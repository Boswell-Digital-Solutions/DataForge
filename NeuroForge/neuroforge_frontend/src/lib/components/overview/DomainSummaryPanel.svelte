<script lang="ts">
  import type { DomainAdapter } from '$lib/types/overview';
  import { Domain } from '$lib/types';

  export let domains: DomainAdapter[] = [];

  function getDomainLabel(domain: string): string {
    const labels = {
      [Domain.LITERARY]: '📚 Literary',
      [Domain.MARKET]: '📈 Market',
      [Domain.GENERAL]: '🧠 General',
    };
    return labels[domain] || domain;
  }

  function getQualityColor(score: number): string {
    if (score >= 0.9) return 'text-green-400';
    if (score >= 0.8) return 'text-yellow-400';
    return 'text-red-400';
  }
</script>

<div class="bg-forge-ash-900 border border-forge-ash-700 rounded-lg overflow-hidden">
  <div class="px-6 py-4 border-b border-forge-ash-700 bg-forge-ash-800">
    <h3 class="text-lg font-semibold text-forge-ink-50">Domain Adapters</h3>
  </div>

  <div class="grid grid-cols-1 md:grid-cols-3 gap-4 p-6">
    {#each domains as domain (domain.domain)}
      <div class="bg-forge-ash-800 border border-forge-ash-700 rounded-lg p-4">
        <div class="flex items-center justify-between mb-4">
          <h4 class="font-semibold text-forge-ink-50">{getDomainLabel(domain.domain)}</h4>
          {#if domain.isActive}
            <span class="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded">Active</span>
          {:else}
            <span class="px-2 py-1 bg-gray-500/20 text-gray-400 text-xs rounded">Inactive</span>
          {/if}
        </div>

        <div class="space-y-2 text-sm">
          <div class="flex justify-between">
            <span class="text-forge-ink-dim">Models Running</span>
            <span class="text-forge-ink-50 font-semibold">{domain.modelsRunning}</span>
          </div>

          <div class="flex justify-between">
            <span class="text-forge-ink-dim">Processed (24h)</span>
            <span class="text-forge-ink-50 font-semibold">{domain.requestsProcessed.toLocaleString()}</span>
          </div>

          <div class="border-t border-forge-ash-700 my-3 pt-3">
            <p class="text-xs text-forge-ink-dim mb-2">Quality Metrics</p>

            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <span class="text-xs text-forge-ink-dim">Coherence</span>
                <span class="text-xs font-semibold text-forge-ink-50">
                  {(domain.evaluationMetrics.coherence * 100).toFixed(0)}%
                </span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-xs text-forge-ink-dim">Relevance</span>
                <span class="text-xs font-semibold text-forge-ink-50">
                  {(domain.evaluationMetrics.relevance * 100).toFixed(0)}%
                </span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-xs text-forge-ink-dim">Factuality</span>
                <span class="text-xs font-semibold text-forge-ink-50">
                  {(domain.evaluationMetrics.factuality * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>

          <div class="flex justify-between text-xs">
            <span class="text-forge-ink-dim">Overall Quality</span>
            <span class={`font-semibold ${getQualityColor(domain.averageQuality)}`}>
              {(domain.averageQuality * 100).toFixed(1)}%
            </span>
          </div>
        </div>
      </div>
    {/each}
  </div>
</div>
