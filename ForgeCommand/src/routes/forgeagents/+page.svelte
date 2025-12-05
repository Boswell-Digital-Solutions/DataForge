<script lang="ts">
	import { onMount } from 'svelte';
	import { invoke } from '@tauri-apps/api/core';
	import LineChart from '$lib/components/LineChart.svelte';

	// Types
	interface ForgeAgentsMetrics {
		active_agents: number;
		total_tasks: number;
		avg_latency_ms: number;
		success_rate: number;
		recent_agents: AgentInfo[];
	}

	interface AgentInfo {
		agent_id: string;
		agent_name: string;
		status: string;
		tasks_completed: number;
		avg_latency_ms: number;
	}

	interface TimeSeriesPoint {
		timestamp: string;
		value: number;
	}

	interface AgentActivityOverTime {
		datapoints: TimeSeriesPoint[];
	}

	interface AgentLatencyOverTime {
		datapoints: TimeSeriesPoint[];
	}

	// State
	let metrics: ForgeAgentsMetrics | null = null;
	let activityData: AgentActivityOverTime | null = null;
	let latencyData: AgentLatencyOverTime | null = null;
	let loading = true;
	let error: string | null = null;

	// Fetch data
	async function fetchData() {
		try {
			loading = true;
			error = null;

			// Fetch all data in parallel
			const [metricsData, activityDataRaw, latencyDataRaw] = await Promise.all([
				invoke<ForgeAgentsMetrics>('get_forgeagents_metrics'),
				invoke<AgentActivityOverTime>('get_agent_activity_over_time', { hours: 24 }),
				invoke<AgentLatencyOverTime>('get_agent_latency_over_time', { hours: 24 })
			]);

			metrics = metricsData;
			activityData = activityDataRaw;
			latencyData = latencyDataRaw;
		} catch (e) {
			error = e as string;
			console.error('Failed to fetch ForgeAgents metrics:', e);
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
	function formatLatency(ms: number): string {
		if (ms < 1000) {
			return `${ms.toFixed(0)}ms`;
		}
		return `${(ms / 1000).toFixed(2)}s`;
	}

	function formatPercentage(value: number): string {
		return `${value.toFixed(1)}%`;
	}

	function getLatencyClass(latency: number): string {
		if (latency < 500) return 'text-green-400';
		if (latency < 1000) return 'text-yellow-400';
		return 'text-red-400';
	}

	function getStatusClass(status: string): string {
		if (status === 'active') return 'text-green-400';
		if (status === 'idle') return 'text-yellow-400';
		return 'text-forge-steel';
	}
</script>

<svelte:head>
	<title>Forge Command - ForgeAgents</title>
</svelte:head>

<div class="space-y-8">
	<!-- Page Header -->
	<div>
		<h1 class="text-4xl font-display font-bold mb-2">
			<span class="text-agents">ForgeAgents</span> Analytics
		</h1>
		<p class="text-forge-steel">Agent orchestration, task execution, and performance monitoring</p>
	</div>

	{#if error}
		<!-- Error State -->
		<div class="panel border-forge-ember bg-forge-ember/10">
			<p class="text-forge-ember font-semibold">Error: {error}</p>
			<button
				onclick={fetchData}
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
			<!-- Active Agents -->
			<div class="kpi-card agents">
				<div class="mb-2">
					<p class="text-sm text-forge-steel uppercase tracking-wide">Active Agents</p>
				</div>
				<div>
					<p class="text-3xl font-bold text-agents">{metrics.active_agents.toLocaleString()}</p>
				</div>
			</div>

			<!-- Total Tasks -->
			<div class="kpi-card agents">
				<div class="mb-2">
					<p class="text-sm text-forge-steel uppercase tracking-wide">Total Tasks</p>
				</div>
				<div>
					<p class="text-3xl font-bold text-agents">{metrics.total_tasks.toLocaleString()}</p>
				</div>
			</div>

			<!-- Avg Latency -->
			<div class="kpi-card agents">
				<div class="mb-2">
					<p class="text-sm text-forge-steel uppercase tracking-wide">Avg Latency</p>
				</div>
				<div>
					<p class="text-3xl font-bold {getLatencyClass(metrics.avg_latency_ms)}">
						{formatLatency(metrics.avg_latency_ms)}
					</p>
				</div>
			</div>

			<!-- Success Rate -->
			<div class="kpi-card agents">
				<div class="mb-2">
					<p class="text-sm text-forge-steel uppercase tracking-wide">Success Rate</p>
				</div>
				<div>
					<p class="text-3xl font-bold text-agents">{formatPercentage(metrics.success_rate)}</p>
				</div>
			</div>
		</div>

		<!-- Top Agents Table -->
		<div>
			<h2 class="text-2xl font-display font-semibold mb-4 text-agents">Top Performing Agents</h2>
			<div class="panel">
				{#if metrics.recent_agents.length === 0}
					<p class="text-forge-steel text-center py-8">No agent activity data yet</p>
				{:else}
					<div class="overflow-x-auto">
						<table class="w-full">
							<thead>
								<tr class="border-b border-forge-steel/30">
									<th class="text-left py-3 px-4 text-sm font-semibold text-forge-steel uppercase tracking-wide">Agent</th>
									<th class="text-left py-3 px-4 text-sm font-semibold text-forge-steel uppercase tracking-wide">Status</th>
									<th class="text-right py-3 px-4 text-sm font-semibold text-forge-steel uppercase tracking-wide">Tasks Completed</th>
									<th class="text-right py-3 px-4 text-sm font-semibold text-forge-steel uppercase tracking-wide">Avg Latency</th>
								</tr>
							</thead>
							<tbody>
								{#each metrics.recent_agents as agent}
									<tr class="border-b border-forge-steel/20 last:border-0 hover:bg-forge-steel/10 transition-colors">
										<td class="py-3 px-4">
											<div>
												<p class="font-mono text-agents font-semibold">{agent.agent_name}</p>
												<p class="text-xs text-forge-steel font-mono">{agent.agent_id}</p>
											</div>
										</td>
										<td class="py-3 px-4">
											<span class="font-mono {getStatusClass(agent.status)} font-semibold">
												{agent.status.toUpperCase()}
											</span>
										</td>
										<td class="py-3 px-4 text-right font-mono">
											{agent.tasks_completed.toLocaleString()}
										</td>
										<td class="py-3 px-4 text-right font-mono {getLatencyClass(agent.avg_latency_ms)}">
											{formatLatency(agent.avg_latency_ms)}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}
			</div>
		</div>

		<!-- Agent Activity Over Time Chart -->
		<div>
			<h2 class="text-2xl font-display font-semibold mb-4 text-agents">Agent Activity Over Time (Last 24 Hours)</h2>
			<div class="panel">
				{#if activityData && activityData.datapoints.length > 0}
					<LineChart
						title="Tasks Completed"
						labels={activityData.datapoints.map(d => d.timestamp.split(' ')[1])}
						data={activityData.datapoints.map(d => d.value)}
						color="#F59E0B"
						yAxisLabel="Tasks"
						xAxisLabel="Hour"
					/>
				{:else}
					<p class="text-forge-steel text-center py-8">No agent activity data available yet</p>
				{/if}
			</div>
		</div>

		<!-- Agent Latency Over Time Chart -->
		<div>
			<h2 class="text-2xl font-display font-semibold mb-4 text-agents">Agent Latency Over Time (Last 24 Hours)</h2>
			<div class="panel">
				{#if latencyData && latencyData.datapoints.length > 0}
					<LineChart
						title="Avg Latency (ms)"
						labels={latencyData.datapoints.map(d => d.timestamp.split(' ')[1])}
						data={latencyData.datapoints.map(d => d.value)}
						color="#F59E0B"
						yAxisLabel="Latency (ms)"
						xAxisLabel="Hour"
					/>
				{:else}
					<p class="text-forge-steel text-center py-8">No latency data available yet</p>
				{/if}
			</div>
		</div>
	{/if}
</div>
