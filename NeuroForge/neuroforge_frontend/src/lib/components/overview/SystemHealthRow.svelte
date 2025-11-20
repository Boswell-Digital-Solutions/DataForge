<script lang="ts">
  import type { SystemHealthMetric } from '$lib/types/overview';

  export let metrics: SystemHealthMetric[] = [];

  function getTrendIcon(trend?: string): string {
    if (trend === 'up') return '↑';
    if (trend === 'down') return '↓';
    return '→';
  }

  function getStatusColor(status: string): string {
    switch (status) {
      case 'healthy':
        return 'text-green-500';
      case 'warning':
        return 'text-yellow-500';
      case 'critical':
        return 'text-red-500';
      default:
        return 'text-forge-ink-dim';
    }
  }
</script>

<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
  {#each metrics as metric (metric.id)}
    <div class="bg-forge-ash-900 border border-forge-ash-700 rounded-lg p-6 hover:border-nf-neural-blue transition-colors">
      <div class="flex items-start justify-between mb-4">
        <div>
          <p class="text-forge-ink-dim text-sm font-medium">{metric.label}</p>
          {#if metric.unit}
            <p class="text-xs text-forge-ink-dim mt-1">({metric.unit})</p>
          {/if}
        </div>
        {#if metric.icon}
          <span class="text-xl">{metric.icon}</span>
        {/if}
      </div>

      <div class="flex items-baseline justify-between">
        <p class="text-3xl font-bold text-forge-ink-50">{metric.value}</p>
        {#if metric.trend}
          <div class={getStatusColor(metric.status)}>
            <span>{getTrendIcon(metric.trend)}</span>
            {#if metric.trendValue}
              <span class="text-sm font-semibold">
                {Math.abs(metric.trendValue).toFixed(1)}%
              </span>
            {/if}
          </div>
        {/if}
      </div>

      <div class="mt-3 h-1 bg-forge-ash-700 rounded-full overflow-hidden">
        <div class="h-full transition-all" class:bg-green-500={metric.status === 'healthy'} class:bg-yellow-500={metric.status === 'warning'} class:bg-red-500={metric.status === 'critical'} style="width: {Math.min(100, Math.max(0, Number(metric.value) || 0))}%" />
      </div>
    </div>
  {/each}
</div>
