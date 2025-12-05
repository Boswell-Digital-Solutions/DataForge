<script lang="ts">
	import { onMount } from 'svelte';
	import { invoke } from '@tauri-apps/api/core';
	import LineChart from '$lib/components/LineChart.svelte';

	// Types
	interface NeuroForgeMetrics {
		total_requests: number;
		total_tokens: number;
		total_cost: number;
		avg_evaluation_score: number;
		top_models: ModelMetric[];
	}

	interface ModelMetric {
		model: string;
		requests: number;
		tokens: number;
		cost: number;
	}

	interface TimeSeriesPoint {
		timestamp: string;
		value: number;
	}

	interface CostOverTime {
		datapoints: TimeSeriesPoint[];
	}

	interface TokenUsageOverTime {
		datapoints: TimeSeriesPoint[];
	}

	// State
	let metrics: NeuroForgeMetrics | null = null;
	let costData: CostOverTime | null = null;
	let tokenData: TokenUsageOverTime | null = null;
	let loading = true;
	let error: string | null = null;

	// Fetch data
	async function fetchData() {
		try {
			loading = true;
			error = null;

			// Fetch all data in parallel
			const [metricsData, costDataRaw, tokenDataRaw] = await Promise.all([
				invoke<NeuroForgeMetrics>('get_neuroforge_metrics'),
				invoke<CostOverTime>('get_cost_over_time', { hours: 24 }),
				invoke<TokenUsageOverTime>('get_token_usage_over_time', { hours: 24 })
			]);

			metrics = metricsData;
			costData = costDataRaw;
			tokenData = tokenDataRaw;
		} catch (e) {
			error = e as string;
			console.error('Failed to fetch NeuroForge metrics:', e);
		} finally {
			loading = false;
		}
	}

	// Auto-refresh every 30 seconds
	onMount(() => {
		fetchData();
		const interval = setInterval(fetchData, 30000);
		return () => clearInterval(interval);
	});

	// Utility functions
	function formatCost(cost: number): string {
		return `$${cost.toFixed(4)}`;
	}

	function formatTokens(tokens: number): string {
		if (tokens >= 1000000) {
			return `${(tokens / 1000000).toFixed(2)}M`;
		} else if (tokens >= 1000) {
			return `${(tokens / 1000).toFixed(2)}K`;
		}
		return tokens.toString();
	}

	function formatScore(score: number): string {
		return `${(score * 100).toFixed(1)}%`;
	}
</script>

<svelte:head>
	<title>Forge Command - NeuroForge</title>
</svelte:head>

<div class="space-y-8">
	<!-- Page Header -->
	<div>
		<h1 class="text-4xl font-display font-bold mb-2">
			<span class="text-neuroforge">NeuroForge</span> Analytics
		</h1>
		<p class="text-forge-steel">LLM usage, cost tracking, and model performance metrics</p>
	</div>

	{#if error}
		<!-- Error State -->
		<div class="panel border-forge-ember bg-forge-ember/10">
			<p class="text-forge-ember font-semibold">Error: {error}</p>
			<button
				on:click={fetchData}
				class="mt-4 px-4 py-2 bg-forge-ember text-white rounded hover:bg-forge-ember/80 transition-colors"
			>
				Retry
			</button>
		</div>
	{:else if loading}
		<!-- Loading State -->
		<div class="grid grid-cols-4 gap-6">
			{#each [1, 2, 3, 4] as _}
				<div class="panel loading-skeleton h-32"></div>
			{/each}
		</div>
	{:else if metrics}
		<!-- Key Metrics Cards -->
		<div class="grid grid-cols-4 gap-6">
			<!-- Total Requests -->
			<div class="kpi-card neuroforge">
				<div class="mb-2">
					<p class="text-sm text-forge-steel uppercase tracking-wide">Total Requests</p>
				</div>
				<div>
					<p class="text-3xl font-bold text-neuroforge">{metrics.total_requests.toLocaleString()}</p>
				</div>
			</div>

			<!-- Total Tokens -->
			<div class="kpi-card neuroforge">
				<div class="mb-2">
					<p class="text-sm text-forge-steel uppercase tracking-wide">Total Tokens</p>
				</div>
				<div>
					<p class="text-3xl font-bold text-neuroforge">{formatTokens(metrics.total_tokens)}</p>
				</div>
			</div>

			<!-- Total Cost -->
			<div class="kpi-card neuroforge">
				<div class="mb-2">
					<p class="text-sm text-forge-steel uppercase tracking-wide">Total Cost</p>
				</div>
				<div>
					<p class="text-3xl font-bold text-neuroforge">{formatCost(metrics.total_cost)}</p>
				</div>
			</div>

			<!-- Avg Quality Score -->
			<div class="kpi-card neuroforge">
				<div class="mb-2">
					<p class="text-sm text-forge-steel uppercase tracking-wide">Avg Quality</p>
				</div>
				<div>
					<p class="text-3xl font-bold text-neuroforge">{formatScore(metrics.avg_evaluation_score)}</p>
				</div>
			</div>
		</div>

		<!-- Top Models Table -->
		<div>
			<h2 class="text-2xl font-display font-semibold mb-4 text-neuroforge">Model Breakdown</h2>
			<div class="panel">
				{#if metrics.top_models.length === 0}
					<p class="text-forge-steel text-center py-8">No model usage data yet</p>
				{:else}
					<div class="overflow-x-auto">
						<table class="w-full">
							<thead>
								<tr class="border-b border-forge-steel/30">
									<th class="text-left py-3 px-4 text-sm font-semibold text-forge-steel uppercase tracking-wide">Model</th>
									<th class="text-right py-3 px-4 text-sm font-semibold text-forge-steel uppercase tracking-wide">Requests</th>
									<th class="text-right py-3 px-4 text-sm font-semibold text-forge-steel uppercase tracking-wide">Tokens</th>
									<th class="text-right py-3 px-4 text-sm font-semibold text-forge-steel uppercase tracking-wide">Cost</th>
									<th class="text-right py-3 px-4 text-sm font-semibold text-forge-steel uppercase tracking-wide">Avg Cost/Req</th>
								</tr>
							</thead>
							<tbody>
								{#each metrics.top_models as model}
									<tr class="border-b border-forge-steel/20 last:border-0 hover:bg-forge-steel/10 transition-colors">
										<td class="py-3 px-4">
											<span class="font-mono text-neuroforge">{model.model}</span>
										</td>
										<td class="py-3 px-4 text-right font-mono">
											{model.requests.toLocaleString()}
										</td>
										<td class="py-3 px-4 text-right font-mono">
											{formatTokens(model.tokens)}
										</td>
										<td class="py-3 px-4 text-right font-mono text-neuroforge">
											{formatCost(model.cost)}
										</td>
										<td class="py-3 px-4 text-right font-mono text-forge-steel">
											{formatCost(model.cost / model.requests)}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}
			</div>
		</div>

		<!-- Cost Over Time Chart -->
		<div>
			<h2 class="text-2xl font-display font-semibold mb-4 text-neuroforge">Cost Over Time (Last 24 Hours)</h2>
			<div class="panel">
				{#if costData && costData.datapoints.length > 0}
					<LineChart
						title="Cost (USD)"
						labels={costData.datapoints.map(d => d.timestamp.split(' ')[1])}
						data={costData.datapoints.map(d => d.value)}
						color="#A855F7"
						yAxisLabel="Cost (USD)"
						xAxisLabel="Hour"
					/>
				{:else}
					<p class="text-forge-steel text-center py-8">No cost data available yet</p>
				{/if}
			</div>
		</div>

		<!-- Token Usage Over Time Chart -->
		<div>
			<h2 class="text-2xl font-display font-semibold mb-4 text-neuroforge">Token Usage Over Time (Last 24 Hours)</h2>
			<div class="panel">
				{#if tokenData && tokenData.datapoints.length > 0}
					<LineChart
						title="Tokens"
						labels={tokenData.datapoints.map(d => d.timestamp.split(' ')[1])}
						data={tokenData.datapoints.map(d => d.value)}
						color="#A855F7"
						yAxisLabel="Total Tokens"
						xAxisLabel="Hour"
					/>
				{:else}
					<p class="text-forge-steel text-center py-8">No token usage data available yet</p>
				{/if}
			</div>
		</div>
	{/if}
</div>
