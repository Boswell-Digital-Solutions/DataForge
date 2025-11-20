<!-- @component
no description yet
-->
<script lang="ts">
  export let loading = false;
  export let disabled = false;
  export let onClick: (() => void) | (() => Promise<void>) | null = null;
  export let variant: "primary" | "secondary" | "danger" = "primary";

  const baseClasses =
    "px-4 py-2 rounded-lg font-medium text-sm transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed";

  const variantClasses: Record<string, string> = {
    primary:
      "bg-forge-ember-500 text-white hover:bg-forge-ember-600 dark:bg-forge-ember-600 dark:hover:bg-forge-ember-700",
    secondary:
      "bg-forge-ash-200 text-forge-ink-900 hover:bg-forge-ash-300 dark:bg-forge-ash-700 dark:text-forge-ash-50 dark:hover:bg-forge-ash-600",
    danger:
      "bg-forge-brass-500 text-white hover:bg-forge-brass-600 dark:bg-forge-brass-600 dark:hover:bg-forge-brass-700",
  };

  async function handleClick() {
    if (onClick) {
      await onClick();
    }
  }
</script>

<button
  on:click={handleClick}
  disabled={loading || disabled}
  class="{baseClasses} {variantClasses[variant]}"
>
  {#if loading}
    <span class="inline-flex items-center space-x-2">
      <svg class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
        <circle
          class="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          stroke-width="4"
        />
        <path
          class="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
      <slot />
    </span>
  {:else}
    <slot />
  {/if}
</button>

<style>
</style>
