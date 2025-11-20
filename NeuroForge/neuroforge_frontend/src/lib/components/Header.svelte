<!-- @component
no description yet
-->
<script lang="ts">
  export let title: string = "NeuroForge";
  export let loading = false;
</script>

<header
  class="sticky top-0 z-50 border-b border-forge-ash-200 bg-forge-ash-50 dark:border-forge-ash-800 dark:bg-forge-ash-950"
>
  <div class="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div
          class="h-8 w-8 rounded-lg bg-gradient-to-br from-forge-ember-500 to-forge-brass-500"
        />
        <h1 class="text-xl font-bold text-forge-ink-900 dark:text-forge-ash-50">
          {title}
        </h1>
      </div>
      {#if loading}
        <div class="flex items-center space-x-2">
          <div
            class="h-4 w-4 animate-spin rounded-full border-2 border-forge-ember-500 border-t-transparent"
          />
          <span class="text-sm text-forge-ash-600 dark:text-forge-ash-400"
            >Loading...</span
          >
        </div>
      {/if}
    </div>
  </div>
</header>

<style>
</style>
