<script lang="ts">
	import { onMount } from 'svelte';
	import { invoke } from '@tauri-apps/api/core';
	import LineChart from '$lib/components/LineChart.svelte';
	import { exportToCSV, exportChartToPNG } from '$lib/utils/exports';

	// Types
	interface DataForgeMetrics {
		total_searches: number;
		avg_search_duration: number;
		avg_similarity: number;
		error_rate: number;
	}

	interface TimeSeriesPoint {
		timestamp: string;
		value: number;
	}

	interface SearchPerformanceOverTime {
		datapoints: TimeSeriesPoint[];
	}

	// State
	let metrics: DataForgeMetrics | null = null;
	let performanceData: SearchPerformanceOverTime | null = null;
	let loading = true;
	let error: string | null = null;
	let performanceChartCanvas: HTMLCanvasElement | null = null;

	// Fetch data
	async function fetchData() {
		try {
			loading = true;
			error = null;

			// Fetch metrics and performance data in parallel
			const [metricsData, perfData] = await Promise.all([
				invoke<DataForgeMetrics>('get_dataforge_metrics'),
				invoke<SearchPerformanceOverTime>('get_search_performance_over_time', { hours: 24 })
			]);

			metrics = metricsData;
			performanceData = perfData;
		} catch (e) {
			error = e as string;
			console.error('Failed to fetch DataForge metrics:', e);
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
	function formatDuration(ms: number): string {
		if (ms < 1000) {
			return `${ms.toFixed(0)}ms`;
		}
		return `${(ms / 1000).toFixed(2)}s`;
	}

	function formatPercentage(value: number): string {
		return `${(value * 100).toFixed(2)}%`;
	}

	function getPerformanceClass(duration: number): string {
		if (duration < 500) return 'text-green-400';
		if (duration < 1000) return 'text-yellow-400';
		return 'text-red-400';
	}

	// Export functions
	function handleExportMetricsCSV() {
		if (!metrics) {
			alert('No metrics data to export');
			return;
		}

		// Export metrics data
		const exportData = [
			{
				metric: 'Total Searches',
				value: metrics.total_searches.toString()
			},
			{
				metric: 'Avg Search Duration',
				value: formatDuration(metrics.avg_search_duration)
			},
			{
				metric: 'Avg Similarity',
				value: formatPercentage(metrics.avg_similarity)
			},
			{
				metric: 'Error Rate',
				value: formatPercentage(metrics.error_rate)
			}
		];

		exportToCSV(exportData, 'dataforge_metrics');
	}

	function handleExportPerformanceChart() {
		if (!performanceChartCanvas) {
			// Try to find the canvas element
			const chartElements = document.querySelectorAll('canvas');
			performanceChartCanvas = chartElements[0] as HTMLCanvasElement || null;
		}

		if (!performanceChartCanvas) {
			alert('Performance chart not found. Please try again.');
			return;
		}

		exportChartToPNG(performanceChartCanvas, 'dataforge_performance_chart');
	}

	// Update canvas reference when chart is rendered
	onMount(() => {
		// Wait a bit for chart to render
		setTimeout(() => {
			const chartElements = document.querySelectorAll('canvas');
			if (chartElements.length > 0) {
				performanceChartCanvas = chartElements[0] as HTMLCanvasElement;
			}
		}, 1000);
	});
</script>

<svelte:head>
	<title>Forge Command - DataForge</title>
</svelte:head>

<div class="space-y-8">
	<!-- Page Header -->
	<div>
		<div class="flex justify-between items-start mb-2">
			<div>
				<h1 class="text-4xl font-display font-bold mb-2">
					<span class="text-dataforge">DataForge</span> Analytics
				</h1>
				<p class="text-forge-steel">Vector search performance, query metrics, and storage analytics</p>
			</div>
			{#if metrics}
				<div class="flex gap-3">
					<button
						on:click={handleExportMetricsCSV}
						class="export-button dataforge"
						title="Export Metrics to CSV"
					>
						<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
							<path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
						</svg>
						<span>Export CSV</span>
					</button>
					<button
						on:click={handleExportPerformanceChart}
						class="export-button dataforge"
						title="Export Performance Chart"
					>
						<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
							<path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd" />
						</svg>
						<span>Performance Chart</span>
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
			<!-- Total Searches -->
			<div class="kpi-card dataforge">
				<div class="mb-2">
					<p class="text-sm text-forge-steel uppercase tracking-wide">Total Searches</p>
				</div>
				<div>
					<p class="text-3xl font-bold text-dataforge">{metrics.total_searches.toLocaleString()}</p>
				</div>
			</div>

			<!-- Avg Search Duration -->
			<div class="kpi-card dataforge">
				<div class="mb-2">
					<p class="text-sm text-forge-steel uppercase tracking-wide">Avg Duration</p>
				</div>
				<div>
					<p class="text-3xl font-bold {getPerformanceClass(metrics.avg_search_duration)}">
						{formatDuration(metrics.avg_search_duration)}
					</p>
				</div>
			</div>

			<!-- Avg Similarity -->
			<div class="kpi-card dataforge">
				<div class="mb-2">
					<p class="text-sm text-forge-steel uppercase tracking-wide">Avg Similarity</p>
				</div>
				<div>
					<p class="text-3xl font-bold text-dataforge">{formatPercentage(metrics.avg_similarity)}</p>
				</div>
			</div>

			<!-- Error Rate -->
			<div class="kpi-card dataforge">
				<div class="mb-2">
					<p class="text-sm text-forge-steel uppercase tracking-wide">Error Rate</p>
				</div>
				<div>
					<p class="text-3xl font-bold" class:text-green-400={metrics.error_rate === 0} class:text-red-400={metrics.error_rate > 0}>
						{formatPercentage(metrics.error_rate)}
					</p>
				</div>
			</div>
		</div>

		<!-- Performance Breakdown -->
		<div>
			<h2 class="text-2xl font-display font-semibold mb-4 text-dataforge">Performance Details</h2>
			<div class="grid grid-cols-2 gap-6">
				<!-- Search Performance -->
				<div class="panel">
					<h3 class="text-lg font-semibold mb-4 text-dataforge">Search Performance</h3>
					<div class="space-y-3">
						<div class="flex justify-between items-center py-2 border-b border-forge-steel/20">
							<span class="text-forge-steel">Total Queries</span>
							<span class="font-mono font-semibold">{metrics.total_searches.toLocaleString()}</span>
						</div>
						<div class="flex justify-between items-center py-2 border-b border-forge-steel/20">
							<span class="text-forge-steel">Avg Response Time</span>
							<span class="font-mono font-semibold {getPerformanceClass(metrics.avg_search_duration)}">
								{formatDuration(metrics.avg_search_duration)}
							</span>
						</div>
						<div class="flex justify-between items-center py-2 border-b border-forge-steel/20">
							<span class="text-forge-steel">Avg Similarity Score</span>
							<span class="font-mono font-semibold text-dataforge">{formatPercentage(metrics.avg_similarity)}</span>
						</div>
						<div class="flex justify-between items-center py-2">
							<span class="text-forge-steel">Error Rate</span>
							<span class="font-mono font-semibold" class:text-green-400={metrics.error_rate === 0} class:text-red-400={metrics.error_rate > 0}>
								{formatPercentage(metrics.error_rate)}
							</span>
						</div>
					</div>
				</div>

				<!-- Performance Distribution (placeholder) -->
				<div class="panel">
					<h3 class="text-lg font-semibold mb-4 text-dataforge">Response Time Distribution</h3>
					<div class="flex items-center justify-center h-48">
						<p class="text-forge-steel">Chart visualization coming soon...</p>
					</div>
				</div>
			</div>
		</div>

		<!-- Search Performance Over Time Chart -->
		<div>
			<h2 class="text-2xl font-display font-semibold mb-4 text-dataforge">Search Performance Over Time (Last 24 Hours)</h2>
			<div class="panel">
				{#if performanceData && performanceData.datapoints.length > 0}
					<LineChart
						title="Avg Response Time (ms)"
						labels={performanceData.datapoints.map(d => d.timestamp.split(' ')[1])}
						data={performanceData.datapoints.map(d => d.value)}
						color="#00A3FF"
						yAxisLabel="Duration (ms)"
						xAxisLabel="Hour"
					/>
				{:else}
					<p class="text-forge-steel text-center py-8">No search performance data available yet</p>
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

	.export-button.dataforge {
		background: rgba(0, 163, 255, 0.1);
		border: 1px solid rgba(0, 163, 255, 0.3);
		color: #00A3FF;
	}

	.export-button.dataforge:hover {
		background: rgba(0, 163, 255, 0.2);
		border-color: #00A3FF;
		transform: translateY(-1px);
		box-shadow: 0 4px 12px rgba(0, 163, 255, 0.2);
	}

	.export-button:active {
		transform: translateY(0);
	}

	.export-button svg {
		width: 1.25rem;
		height: 1.25rem;
	}
</style>
