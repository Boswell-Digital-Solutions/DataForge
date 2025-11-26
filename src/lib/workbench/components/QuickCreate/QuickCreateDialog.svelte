<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  interface Props {
    isOpen?: boolean;
    onClose?: () => void;
  }

  let { isOpen = false, onClose }: Props = $props();

  const dispatch = createEventDispatcher();

  // Form state
  let projectName = $state('');
  let language = $state('typescript');
  let stack = $state('sveltekit');
  let projectPath = $state('');

  // Validation
  const canCreate = $derived(projectName.trim().length >= 2 && projectName.trim().length <= 50);

  function handleClose() {
    onClose?.();
    dispatch('close');
  }

  function handleCreate() {
    if (!canCreate) return;

    dispatch('create', {
      projectName: projectName.trim(),
      language,
      stack,
      projectPath: projectPath.trim() || '~',
    });

    // Close after creation
    handleClose();
  }

  function handleOpenWizard() {
    dispatch('open-wizard');
    handleClose();
  }

  function handleKeydown(event: KeyboardEvent) {
    if (!isOpen) return;

    if (event.key === 'Escape') {
      handleClose();
    } else if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      event.preventDefault();
      handleCreate();
    }
  }
</script>

{#if isOpen}
  <svelte:window onkeydown={handleKeydown} />

  <!-- Backdrop -->
  <div
    class="fixed inset-0 bg-black/50 z-40"
    onclick={handleClose}
    role="presentation"
  ></div>

  <!-- Dialog -->
  <div
    class="fixed inset-0 z-50 flex items-center justify-center p-4"
    role="dialog"
    aria-modal="true"
    aria-labelledby="quick-create-title"
  >
    <div
      class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6"
      onclick={(e) => e.stopPropagation()}
    >
      <!-- Header -->
      <div class="flex items-center justify-between mb-4">
        <h2 id="quick-create-title" class="text-xl font-semibold text-gray-900 dark:text-white">
          Quick Create
        </h2>
        <button
          onclick={handleClose}
          class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          aria-label="Close"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
        Fast project creation with sensible defaults
      </p>

      <!-- Form -->
      <form onsubmit|preventDefault={handleCreate} class="space-y-4">
        <!-- Project Name -->
        <div>
          <label for="project-name" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Project Name *
          </label>
          <input
            id="project-name"
            type="text"
            bind:value={projectName}
            placeholder="my-awesome-project"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            required
          />
          {#if projectName && (projectName.length < 2 || projectName.length > 50)}
            <p class="text-xs text-red-600 dark:text-red-400 mt-1">
              Name must be between 2 and 50 characters
            </p>
          {/if}
        </div>

        <!-- Language -->
        <div>
          <label for="language" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Language
          </label>
          <select
            id="language"
            bind:value={language}
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="typescript">TypeScript</option>
            <option value="javascript">JavaScript</option>
            <option value="python">Python</option>
            <option value="rust">Rust</option>
          </select>
        </div>

        <!-- Stack -->
        <div>
          <label for="stack" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Stack
          </label>
          <select
            id="stack"
            bind:value={stack}
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="sveltekit">SvelteKit</option>
            <option value="react">React</option>
            <option value="vue">Vue</option>
            <option value="express">Express</option>
          </select>
        </div>

        <!-- Project Path -->
        <div>
          <label for="project-path" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Project Path
          </label>
          <input
            id="project-path"
            type="text"
            bind:value={projectPath}
            placeholder="~"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          />
        </div>

        <!-- Defaults Info -->
        <div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md p-3">
          <p class="text-xs text-blue-800 dark:text-blue-300">
            <strong>Sensible defaults:</strong> Testing enabled, README included, Git initialized, MIT license
          </p>
        </div>

        <!-- Actions -->
        <div class="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
          <button
            type="button"
            onclick={handleOpenWizard}
            class="text-sm text-blue-600 dark:text-blue-400 hover:underline"
          >
            Need more options?
          </button>

          <div class="flex gap-2">
            <button
              type="button"
              onclick={handleClose}
              class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!canCreate}
              class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed rounded-md"
            >
              Create
            </button>
          </div>
        </div>

        <!-- Keyboard Hint -->
        <p class="text-xs text-center text-gray-500 dark:text-gray-400">
          Press <kbd class="px-1 py-0.5 bg-gray-100 dark:bg-gray-700 rounded">⌘</kbd>
          <kbd class="px-1 py-0.5 bg-gray-100 dark:bg-gray-700 rounded">↵</kbd> to create
        </p>
      </form>
    </div>
  </div>
{/if}
