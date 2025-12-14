<script lang="ts">
	import { onMount } from 'svelte';
	import { invoke } from '@tauri-apps/api/core';
	import LineChart from '$lib/components/LineChart.svelte';
	import { exportToCSV, exportChartToPNG } from '$lib/utils/exports';

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
	let costChartCanvas: HTMLCanvasElement | null = null;
	let tokenChartCanvas: HTMLCanvasElement | null = null;

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

	// Export functions
	function handleExportMetricsCSV() {
		if (!metrics) {
			alert('No metrics data to export');
			return;
		}

		// Export metrics and model breakdown
		const exportData = [
			{
				metric: 'Total Requests',
				value: metrics.total_requests.toString()
			},
			{
				metric: 'Total Tokens',
				value: formatTokens(metrics.total_tokens)
			},
			{
				metric: 'Total Cost',
				value: formatCost(metrics.total_cost)
			},
			{
				metric: 'Avg Quality Score',
				value: formatScore(metrics.avg_evaluation_score)
			},
			...metrics.top_models.map(model => ({
				model: model.model,
				requests: model.requests.toString(),
				tokens: formatTokens(model.tokens),
				cost: formatCost(model.cost),
				avg_cost_per_request: formatCost(model.cost / model.requests)
			}))
		];

		exportToCSV(exportData, 'neuroforge_metrics');
	}

	function handleExportCostChart() {
		if (!costChartCanvas) {
			// Try to find the canvas element
			const chartElements = document.querySelectorAll('canvas');
			costChartCanvas = chartElements[0] as HTMLCanvasElement || null;
		}

		if (!costChartCanvas) {
			alert('Cost chart not found. Please try again.');
			return;
		}

		exportChartToPNG(costChartCanvas, 'neuroforge_cost_chart');
	}

	function handleExportTokenChart() {
		if (!tokenChartCanvas) {
			// Try to find the canvas element
			const chartElements = document.querySelectorAll('canvas');
			tokenChartCanvas = chartElements[1] as HTMLCanvasElement || null;
		}

		if (!tokenChartCanvas) {
			alert('Token chart not found. Please try again.');
			return;
		}

		exportChartToPNG(tokenChartCanvas, 'neuroforge_token_chart');
	}

	// Update canvas references when charts are rendered
	onMount(() => {
		// Wait a bit for charts to render
		setTimeout(() => {
			const chartElements = document.querySelectorAll('canvas');
			if (chartElements.length >= 2) {
				costChartCanvas = chartElements[0] as HTMLCanvasElement;
				tokenChartCanvas = chartElements[1] as HTMLCanvasElement;
			}
		}, 1000);
	});
</script>

<svelte:head>
	<title>Forge Command - NeuroForge</title>
</svelte:head>

<div class="space-y-8">
	<!-- Page Header -->
	<div>
		<div class="flex justify-between items-start mb-2">
			<div>
				<h1 class="text-4xl font-display font-bold mb-2">
					<span class="text-neuroforge">NeuroForge</span> Analytics
				</h1>
				<p class="text-forge-steel">LLM usage, cost tracking, and model performance metrics</p>
			</div>
			{#if metrics}
				<div class="flex gap-3">
					<button
						on:click={handleExportMetricsCSV}
						class="export-button neuroforge"
						title="Export Metrics to CSV"
					>
						<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
							<path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
						</svg>
						<span>Export CSV</span>
					</button>
					<button
						on:click={handleExportCostChart}
						class="export-button neuroforge"
						title="Export Cost Chart"
					>
						<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
							<path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd" />
						</svg>
						<span>Cost Chart</span>
					</button>
					<button
						on:click={handleExportTokenChart}
						class="export-button neuroforge"
						title="Export Token Chart"
					>
						<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
							<path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd" />
						</svg>
						<span>Token Chart</span>
					</button>
				</div>
			{/if}
		</div>
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

<style>
	.export-button {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 500;
		transition: all 0.2s ease;
		cursor: pointer;
	}

	.export-button.neuroforge {
		background: rgba(168, 85, 247, 0.1);
		border: 1px solid rgba(168, 85, 247, 0.3);
		color: #A855F7;
	}

	.export-button.neuroforge:hover {
		background: rgba(168, 85, 247, 0.2);
		border-color: #A855F7;
		transform: translateY(-1px);
		box-shadow: 0 4px 12px rgba(168, 85, 247, 0.2);
	}

	.export-button:active {
		transform: translateY(0);
	}

	.export-button svg {
		width: 1.25rem;
		height: 1.25rem;
	}
</style>
