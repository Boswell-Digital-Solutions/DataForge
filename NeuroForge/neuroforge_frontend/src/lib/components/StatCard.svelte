<!-- @component
no description yet
-->
<script lang="ts">
  export let title: string;
  export let value: string | number;
  export let trend: "up" | "down" | "neutral" = "neutral";
  export let trendValue: string = "";
  export let icon: string = "📊";
</script>

<div
  class="rounded-lg border border-forge-ash-200 bg-white p-6 shadow-sm dark:border-forge-ash-700 dark:bg-forge-ash-900"
>
  <div class="flex items-start justify-between">
    <div class="flex-1">
      <p class="text-sm font-medium text-forge-ash-600 dark:text-forge-ash-400">
        {title}
      </p>
      <p
        class="mt-2 text-3xl font-bold text-forge-ink-900 dark:text-forge-ash-50"
      >
        {value}
      </p>
      {#if trendValue}
        <p
          class="mt-2 text-sm {trend === 'up'
            ? 'text-forge-ember-600 dark:text-forge-ember-400'
            : trend === 'down'
            ? 'text-forge-brass-600 dark:text-forge-brass-400'
            : 'text-forge-ash-600 dark:text-forge-ash-400'}"
        >
          {trendValue}
        </p>
      {/if}
    </div>
    <div class="text-3xl">{icon}</div>
  </div>
</div>

<style>
</style>
