<script lang="ts">
	import '../app.css';
</script>

<div class="min-h-screen bg-forge-black fc-app">
	<!-- Header -->
	<header class="fc-topbar border-b border-forge-steel backdrop-blur-sm sticky top-0 z-50">
		<div class="container mx-auto px-6 py-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center space-x-4">
					<h1 class="text-2xl font-display font-bold fc-brand-mark">
						<span class="text-dataforge">Forge</span>
						<span class="text-white fc-brand-name"> Command</span>
					</h1>
					<span class="text-forge-steel text-sm">Mission Control</span>
				</div>

				<nav class="flex items-center space-x-6">
					<a href="/" class="text-white hover:text-dataforge transition-colors">
						Overview
					</a>
					<a href="/dataforge" class="text-white hover:text-dataforge transition-colors">
						DataForge
					</a>
					<a href="/neuroforge" class="text-white hover:text-neuroforge transition-colors">
						NeuroForge
					</a>
					<a href="/forgeagents" class="text-white hover:text-agents transition-colors">
						ForgeAgents
					</a>
					<a href="/rake" class="text-white hover:text-rake transition-colors">
						Rake
					</a>
				</nav>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="container mx-auto px-6 py-8">
		<slot />
	</main>

	<!-- Footer -->
	<footer class="border-t border-forge-steel mt-16">
		<div class="container mx-auto px-6 py-4">
			<p class="text-forge-steel text-sm text-center">
				Forge Command v0.1.0 · Powered by Tauri + SvelteKit
			</p>
		</div>
	</footer>
</div>
