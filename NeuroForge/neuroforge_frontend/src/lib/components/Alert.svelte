<!-- @component
Alert notification component with optional dismiss
-->
<script lang="ts">
  export let message: string = "";
  export let type: "error" | "success" | "info" | "warning" = "error";
  export let onDismiss: (() => void) | null = null;

  const bgColors: Record<string, string> = {
    error: "bg-forge-ember-50 dark:bg-forge-ember-950",
    success: "bg-forge-brass-50 dark:bg-forge-brass-950",
    info: "bg-forge-ash-50 dark:bg-forge-ash-900",
    warning: "bg-forge-ember-50 dark:bg-forge-ember-950",
  };

  const borderColors: Record<string, string> = {
    error: "border-forge-ember-200 dark:border-forge-ember-800",
    success: "border-forge-brass-200 dark:border-forge-brass-800",
    info: "border-forge-ash-200 dark:border-forge-ash-700",
    warning: "border-forge-ember-200 dark:border-forge-ember-800",
  };

  const textColors: Record<string, string> = {
    error: "text-forge-ember-800 dark:text-forge-ember-200",
    success: "text-forge-brass-800 dark:text-forge-brass-200",
    info: "text-forge-ash-800 dark:text-forge-ash-200",
    warning: "text-forge-ember-800 dark:text-forge-ember-200",
  };
</script>

{#if message}
  <div class="rounded-lg border {borderColors[type]} {bgColors[type]} p-4">
    <div class="flex items-start justify-between">
      <p class={`text-sm font-medium ${textColors[type]}`}>
        {message}
        <slot />
      </p>
      {#if onDismiss}
        <button
          on:click={onDismiss}
          class="ml-2 inline-flex text-forge-ash-400 hover:text-forge-ash-600 dark:text-forge-ash-500 dark:hover:text-forge-ash-300"
        >
          <span class="sr-only">Dismiss</span>
          <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path
              fill-rule="evenodd"
              d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
              clip-rule="evenodd"
            />
          </svg>
        </button>
      {/if}
    </div>
  </div>
{/if}

<style>
</style>
