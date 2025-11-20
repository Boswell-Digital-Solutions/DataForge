<script lang="ts">
  import type { ModelStatus } from '$lib/types/overview';

  export let models: ModelStatus[] = [];

  function getStatusBadge(status: string): string {
    switch (status) {
      case 'healthy':
        return 'bg-green-500/20 text-green-400';
      case 'degraded':
        return 'bg-yellow-500/20 text-yellow-400';
      case 'unhealthy':
        return 'bg-red-500/20 text-red-400';
      case 'offline':
        return 'bg-gray-500/20 text-gray-400';
      default:
        return 'bg-forge-ash-800 text-forge-ink-400';
    }
  }

  function getErrorRateColor(rate: number): string {
    if (rate < 0.01) return 'text-green-400';
    if (rate < 0.05) return 'text-yellow-400';
    return 'text-red-400';
  }
</script>

<div class="bg-forge-ash-900 border border-forge-ash-700 rounded-lg overflow-hidden">
  <div class="px-6 py-4 border-b border-forge-ash-700 bg-forge-ash-800">
    <h3 class="text-lg font-semibold text-forge-ink-50">Model Status Grid</h3>
  </div>

  <div class="overflow-x-auto">
    <table class="w-full">
      <thead>
        <tr class="border-b border-forge-ash-700">
          <th class="text-left px-6 py-3 text-xs font-semibold text-forge-ink-dim uppercase">Model</th>
          <th class="text-left px-6 py-3 text-xs font-semibold text-forge-ink-dim uppercase">Provider</th>
          <th class="text-left px-6 py-3 text-xs font-semibold text-forge-ink-dim uppercase">Status</th>
          <th class="text-right px-6 py-3 text-xs font-semibold text-forge-ink-dim uppercase">Latency</th>
          <th class="text-right px-6 py-3 text-xs font-semibold text-forge-ink-dim uppercase">Error Rate</th>
          <th class="text-right px-6 py-3 text-xs font-semibold text-forge-ink-dim uppercase">Availability</th>
          <th class="text-right px-6 py-3 text-xs font-semibold text-forge-ink-dim uppercase">Cost/Req</th>
        </tr>
      </thead>
      <tbody>
        {#each models as model (model.id)}
          <tr class="border-b border-forge-ash-700 hover:bg-forge-ash-800 transition-colors">
            <td class="px-6 py-4">
              <div class="flex items-center gap-2">
                {#if model.isChampion}
                  <span title="Champion Model">👑</span>
                {/if}
                <span class="text-forge-ink-50 font-medium">{model.name}</span>
              </div>
            </td>
            <td class="px-6 py-4">
              <span class="text-sm text-forge-ink-dim capitalize">{model.provider}</span>
            </td>
            <td class="px-6 py-4">
              <span class="px-2 py-1 rounded text-xs font-semibold {getStatusBadge(model.status)}">
                {model.status}
              </span>
            </td>
            <td class="px-6 py-4 text-right">
              <span class="text-sm text-forge-ink-50 font-semibold">{model.latencyMs}ms</span>
            </td>
            <td class="px-6 py-4 text-right">
              <span class="text-sm font-semibold {getErrorRateColor(model.errorRate)}">
                {(model.errorRate * 100).toFixed(2)}%
              </span>
            </td>
            <td class="px-6 py-4 text-right">
              <span class="text-sm text-forge-ink-50 font-semibold">
                {(model.availability * 100).toFixed(1)}%
              </span>
            </td>
            <td class="px-6 py-4 text-right">
              <span class="text-sm text-forge-ink-50 font-semibold">
                ${model.costPerInference.toFixed(4)}
              </span>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</div>
