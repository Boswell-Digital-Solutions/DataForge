<script lang="ts">
	import { onMount } from 'svelte';
	import { invoke } from '@tauri-apps/api/core';
	import LineChart from '$lib/components/LineChart.svelte';

	// Types
	interface RakeMetrics {
		total_pipelines: number;
		active_pipelines: number;
		records_ingested: number;
		ingestion_rate: number;
		error_rate: number;
		recent_pipelines: PipelineInfo[];
	}

	interface PipelineInfo {
		pipeline_id: string;
		pipeline_name: string;
		status: string;
		records_processed: number;
		last_run: string;
	}

	interface IngestionOverTime {
		datapoints: { timestamp: string; value: number }[];
	}

	interface ErrorRateOverTime {
		datapoints: { timestamp: string; value: number }[];
	}

	// State
	let metrics: RakeMetrics | null = null;
	let ingestionData: IngestionOverTime = { datapoints: [] };
	let errorData: ErrorRateOverTime = { datapoints: [] };
	let loading = true;
	let error: string | null = null;

	// Fetch data
	async function fetchData() {
		try {
			loading = true;
			error = null;

			const [metricsData, ingestionDataRaw, errorDataRaw] = await Promise.all([
				invoke<RakeMetrics>('get_rake_metrics'),
				invoke<IngestionOverTime>('get_ingestion_over_time', { hours: 24 }),
				invoke<ErrorRateOverTime>('get_error_rate_over_time', { hours: 24 })
			]);

			metrics = metricsData;
			ingestionData = ingestionDataRaw;
			errorData = errorDataRaw;
		} catch (e) {
			error = e as string;
			console.error('Failed to fetch data:', e);
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
	function formatNumber(num: number): string {
		return num.toLocaleString();
	}

	function formatRate(rate: number): string {
		return `${rate.toFixed(1)}/hr`;
	}

	function formatPercent(percent: number): string {
		return `${percent.toFixed(2)}%`;
	}

	function getStatusClass(status: string): string {
		if (status === 'active') return 'up';
		return 'degraded';
	}

	function formatTimestamp(timestamp: string): string {
		const date = new Date(timestamp);
		return date.toLocaleString();
	}
</script>

<svelte:head>
	<title>Forge Command - Rake</title>
</svelte:head>

<div class="space-y-8">
	<!-- Page Header -->
	<div>
		<h1 class="text-4xl font-display font-bold mb-2">
			<span class="text-rake">Rake</span> Dashboard
		</h1>
		<p class="text-forge-steel">Pipeline status, ingestion metrics, and data flow monitoring</p>
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
		<div class="grid grid-cols-5 gap-6">
			{#each [1, 2, 3, 4, 5] as _}
				<div class="panel loading-skeleton h-32"></div>
			{/each}
		</div>
	{:else if metrics}
		<!-- KPI Cards -->
		<div class="grid grid-cols-5 gap-6">
			<!-- Total Pipelines -->
			<div class="kpi-card rake">
				<div class="mb-4">
					<h3 class="text-sm font-semibold text-forge-steel uppercase tracking-wide mb-2">
						Total Pipelines
					</h3>
					<p class="text-3xl font-bold text-rake">{formatNumber(metrics.total_pipelines)}</p>
				</div>
			</div>

			<!-- Active Pipelines -->
			<div class="kpi-card rake">
				<div class="mb-4">
					<h3 class="text-sm font-semibold text-forge-steel uppercase tracking-wide mb-2">
						Active Pipelines
					</h3>
					<p class="text-3xl font-bold text-rake">{formatNumber(metrics.active_pipelines)}</p>
				</div>
			</div>

			<!-- Records Ingested -->
			<div class="kpi-card rake">
				<div class="mb-4">
					<h3 class="text-sm font-semibold text-forge-steel uppercase tracking-wide mb-2">
						Records Ingested
					</h3>
					<p class="text-3xl font-bold text-rake">{formatNumber(metrics.records_ingested)}</p>
				</div>
			</div>

			<!-- Ingestion Rate -->
			<div class="kpi-card rake">
				<div class="mb-4">
					<h3 class="text-sm font-semibold text-forge-steel uppercase tracking-wide mb-2">
						Ingestion Rate
					</h3>
					<p class="text-3xl font-bold text-rake">{formatRate(metrics.ingestion_rate)}</p>
				</div>
			</div>

			<!-- Error Rate -->
			<div class="kpi-card rake">
				<div class="mb-4">
					<h3 class="text-sm font-semibold text-forge-steel uppercase tracking-wide mb-2">
						Error Rate
					</h3>
					<p class="text-3xl font-bold text-rake">{formatPercent(metrics.error_rate)}</p>
				</div>
			</div>
		</div>

		<!-- Recent Pipelines Table -->
		<div class="panel">
			<h2 class="text-2xl font-display font-semibold mb-4 text-rake">Recent Pipelines</h2>
			<div class="overflow-x-auto">
				<table class="w-full">
					<thead>
						<tr class="border-b border-forge-steel/30">
							<th class="text-left py-3 px-4 text-forge-steel font-semibold">Pipeline</th>
							<th class="text-left py-3 px-4 text-forge-steel font-semibold">Status</th>
							<th class="text-right py-3 px-4 text-forge-steel font-semibold">Records</th>
							<th class="text-right py-3 px-4 text-forge-steel font-semibold">Last Run</th>
						</tr>
					</thead>
					<tbody>
						{#each metrics.recent_pipelines as pipeline}
							<tr class="border-b border-forge-steel/10 hover:bg-forge-steel/5 transition-colors">
								<td class="py-3 px-4">
									<div>
										<div class="font-medium text-white">{pipeline.pipeline_name}</div>
										<div class="text-sm text-forge-steel font-mono">{pipeline.pipeline_id}</div>
									</div>
								</td>
								<td class="py-3 px-4">
									<span class="status-badge {getStatusClass(pipeline.status)} text-xs">
										{pipeline.status}
									</span>
								</td>
								<td class="py-3 px-4 text-right font-mono">
									{formatNumber(pipeline.records_processed)}
								</td>
								<td class="py-3 px-4 text-right font-mono text-sm text-forge-steel">
									{formatTimestamp(pipeline.last_run)}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>

		<!-- Charts -->
		<div class="grid grid-cols-2 gap-6">
			<!-- Ingestion Over Time -->
			<LineChart
				title="Records Ingested (24 Hours)"
				color="#22CFC5"
				data={ingestionData.datapoints.map((d) => d.value)}
				labels={ingestionData.datapoints.map((d) => {
					const date = new Date(d.timestamp);
					return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
				})}
			/>

			<!-- Error Rate Over Time -->
			<LineChart
				title="Error Rate % (24 Hours)"
				color="#D97706"
				data={errorData.datapoints.map((d) => d.value)}
				labels={errorData.datapoints.map((d) => {
					const date = new Date(d.timestamp);
					return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
				})}
			/>
		</div>
	{/if}
</div>
