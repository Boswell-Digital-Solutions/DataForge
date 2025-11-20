<script lang="ts">
  import type { ActivityEntry } from '$lib/types/overview';
  import { Domain } from '$lib/types';

  export let activities: ActivityEntry[] = [];

  function getTypeIcon(type: string): string {
    switch (type) {
      case 'inference':
        return '⚡';
      case 'evaluation':
        return '📊';
      case 'error':
        return '❌';
      case 'system':
        return '⚙️';
      default:
        return '📋';
    }
  }

  function getStatusColor(status: string): string {
    switch (status) {
      case 'completed':
        return 'text-green-400';
      case 'processing':
        return 'text-yellow-400';
      case 'error':
      case 'failed':
        return 'text-red-400';
      default:
        return 'text-forge-ink-dim';
    }
  }

  function getDomainBadge(domain: string): string {
    switch (domain) {
      case Domain.LITERARY:
        return 'bg-purple-500/20 text-purple-300';
      case Domain.MARKET:
        return 'bg-blue-500/20 text-blue-300';
      case Domain.GENERAL:
        return 'bg-cyan-500/20 text-cyan-300';
      default:
        return 'bg-forge-ash-700 text-forge-ink-400';
    }
  }

  function formatTime(iso: string): string {
    return new Date(iso).toLocaleTimeString();
  }
</script>

<div class="bg-forge-ash-900 border border-forge-ash-700 rounded-lg overflow-hidden">
  <div class="px-6 py-4 border-b border-forge-ash-700 bg-forge-ash-800">
    <h3 class="text-lg font-semibold text-forge-ink-50">Recent Activity</h3>
  </div>

  <div class="max-h-96 overflow-y-auto">
    {#if activities.length === 0}
      <div class="px-6 py-8 text-center text-forge-ink-dim">
        <p>No recent activity</p>
      </div>
    {:else}
      {#each activities as activity (activity.id)}
        <div class="px-6 py-4 border-b border-forge-ash-700 hover:bg-forge-ash-800 transition-colors">
          <div class="flex items-start gap-4">
            <div class="text-lg pt-1">{getTypeIcon(activity.type)}</div>

            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <span class="font-semibold text-forge-ink-50">{activity.message}</span>
                <span class="px-2 py-0.5 text-xs rounded {getDomainBadge(activity.domain)}">
                  {activity.domain}
                </span>
              </div>

              <div class="flex items-center gap-4 text-xs text-forge-ink-dim">
                <span>{formatTime(activity.timestamp)}</span>
                <span class={getStatusColor(activity.status)} title={activity.status}>
                  {activity.status}
                </span>
                {#if activity.latencyMs}
                  <span>{activity.latencyMs}ms</span>
                {/if}
                {#if activity.evaluationScore}
                  <span>Score: {(activity.evaluationScore * 100).toFixed(0)}%</span>
                {/if}
              </div>
            </div>
          </div>
        </div>
      {/each}
    {/if}
  </div>
</div>
