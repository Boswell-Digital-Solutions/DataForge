<script lang="ts">
	import { onMount } from 'svelte';
	import { invoke } from '@tauri-apps/api/core';
	import { exportToCSV, exportToPDF } from '$lib/utils/exports';

	// Types
	interface SystemHealth {
		dataforge_status: string;
		dataforge_uptime: number;
		neuroforge_status: string;
		neuroforge_uptime: number;
		rake_status: string;
		rake_uptime: number;
		forgeagents_status: string;
		forgeagents_uptime: number;
	}

	interface RecentEvent {
		event_id: string;
		timestamp: string;
		service: string;
		event_type: string;
		severity: string;
	}

	// State
	let health: SystemHealth | null = null;
	let recentEvents: RecentEvent[] = [];
	let loading = true;
	let error: string | null = null;

	// Fetch data
	async function fetchData() {
		try {
			loading = true;
			error = null;

			const [healthData, eventsData] = await Promise.all([
				invoke<SystemHealth>('get_system_health'),
				invoke<RecentEvent[]>('get_recent_events', { limit: 10 })
			]);

			health = healthData;
			recentEvents = eventsData;
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
	function formatUptime(uptime: number): string {
		return `${uptime.toFixed(1)}%`;
	}

	function getStatusClass(status: string): string {
		if (status === 'UP') return 'up';
		if (status === 'DOWN') return 'down';
		return 'degraded';
	}

	function getServiceColor(service: string): string {
		if (service === 'dataforge') return 'dataforge';
		if (service === 'neuroforge') return 'neuroforge';
		if (service === 'rake') return 'rake';
		if (service === 'forgeagents') return 'agents';
		return 'white';
	}

	function formatTimestamp(timestamp: string): string {
		const date = new Date(timestamp);
		return date.toLocaleTimeString();
	}

	// Export functions
	function handleExportCSV() {
		if (!health || !recentEvents) {
			alert('No data to export');
			return;
		}

		// Combine system health and events into exportable format
		const exportData = [
			{
				section: 'System Health',
				service: 'DataForge',
				status: health.dataforge_status,
				uptime: `${health.dataforge_uptime.toFixed(1)}%`
			},
			{
				section: 'System Health',
				service: 'NeuroForge',
				status: health.neuroforge_status,
				uptime: `${health.neuroforge_uptime.toFixed(1)}%`
			},
			{
				section: 'System Health',
				service: 'ForgeAgents',
				status: health.forgeagents_status,
				uptime: `${health.forgeagents_uptime.toFixed(1)}%`
			},
			{
				section: 'System Health',
				service: 'Rake',
				status: health.rake_status,
				uptime: `${health.rake_uptime.toFixed(1)}%`
			},
			...recentEvents.map(event => ({
				section: 'Recent Events',
				service: event.service,
				event_type: event.event_type,
				severity: event.severity,
				timestamp: event.timestamp
			}))
		];

		exportToCSV(exportData, 'forge_overview');
	}

	function handleExportPDF() {
		if (!health || !recentEvents) {
			alert('No data to export');
			return;
		}

		// Format data for PDF
		const healthData = [
			{
				Service: 'DataForge',
				Status: health.dataforge_status,
				Uptime: `${health.dataforge_uptime.toFixed(1)}%`
			},
			{
				Service: 'NeuroForge',
				Status: health.neuroforge_status,
				Uptime: `${health.neuroforge_uptime.toFixed(1)}%`
			},
			{
				Service: 'ForgeAgents',
				Status: health.forgeagents_status,
				Uptime: `${health.forgeagents_uptime.toFixed(1)}%`
			},
			{
				Service: 'Rake',
				Status: health.rake_status,
				Uptime: `${health.rake_uptime.toFixed(1)}%`
			}
		];

		const eventsData = recentEvents.map(event => ({
			Service: event.service,
			Type: event.event_type,
			Severity: event.severity,
			Time: formatTimestamp(event.timestamp)
		}));

		// Combine all data for PDF
		const allData = [
			...healthData.map(item => ({ ...item, Section: 'System Health' })),
			...eventsData.map(item => ({ ...item, Section: 'Recent Events' }))
		];

		exportToPDF(allData, 'Forge Command - System Overview', 'forge_overview');
	}
</script>

<svelte:head>
	<title>Forge Command - Overview</title>
</svelte:head>

<div class="space-y-8">
	<!-- Page Header -->
	<div class="fc-hero-section">
		<div class="flex justify-between items-start">
			<div>
				<h1 class="text-4xl font-display font-bold mb-2 relative z-10">System Overview</h1>
				<p class="text-forge-steel relative z-10">Real-time monitoring of all Forge services</p>
			</div>
			{#if health}
				<div class="flex gap-3 relative z-10">
					<button
						on:click={handleExportCSV}
						class="export-button"
						title="Export to CSV"
					>
						<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
							<path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
						</svg>
						<span>Export CSV</span>
					</button>
					<button
						on:click={handleExportPDF}
						class="export-button"
						title="Export to PDF"
					>
						<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
							<path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
						</svg>
						<span>Export PDF</span>
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
	{:else if health}
		<!-- Service Health Cards -->
		<div class="grid grid-cols-4 gap-6">
			<!-- DataForge -->
			<div class="kpi-card dataforge fc-service-card fc-service-card--dataforge">
				<div class="flex items-center justify-between mb-4">
					<h3 class="text-xl font-semibold text-dataforge">DataForge</h3>
					<span class="status-badge {getStatusClass(health.dataforge_status)}">
						{health.dataforge_status}
					</span>
				</div>
				<div class="space-y-2">
					<div class="flex justify-between text-sm">
						<span class="text-forge-steel">Uptime</span>
						<span class="font-mono">{formatUptime(health.dataforge_uptime)}</span>
					</div>
					<div class="fc-progress-track fc-progress--dataforge">
						<div class="fc-progress-value" style="width: {health.dataforge_uptime}%"></div>
					</div>
				</div>
			</div>

			<!-- NeuroForge -->
			<div class="kpi-card neuroforge fc-service-card fc-service-card--neuroforge">
				<div class="flex items-center justify-between mb-4">
					<h3 class="text-xl font-semibold text-neuroforge">NeuroForge</h3>
					<span class="status-badge {getStatusClass(health.neuroforge_status)}">
						{health.neuroforge_status}
					</span>
				</div>
				<div class="space-y-2">
					<div class="flex justify-between text-sm">
						<span class="text-forge-steel">Uptime</span>
						<span class="font-mono">{formatUptime(health.neuroforge_uptime)}</span>
					</div>
					<div class="fc-progress-track fc-progress--neuroforge">
						<div class="fc-progress-value" style="width: {health.neuroforge_uptime}%"></div>
					</div>
				</div>
			</div>

			<!-- ForgeAgents -->
			<div class="kpi-card agents fc-service-card fc-service-card--agents fc-sparks">
				<div class="flex items-center justify-between mb-4">
					<h3 class="text-xl font-semibold text-agents">ForgeAgents</h3>
					<span class="status-badge {getStatusClass(health.forgeagents_status)}">
						{health.forgeagents_status}
					</span>
				</div>
				<div class="space-y-2">
					<div class="flex justify-between text-sm">
						<span class="text-forge-steel">Uptime</span>
						<span class="font-mono">{formatUptime(health.forgeagents_uptime)}</span>
					</div>
					<div class="fc-progress-track fc-progress--agents">
						<div class="fc-progress-value" style="width: {health.forgeagents_uptime}%"></div>
					</div>
				</div>
			</div>

			<!-- Rake -->
			<div class="kpi-card rake fc-service-card fc-service-card--rake">
				<div class="flex items-center justify-between mb-4">
					<h3 class="text-xl font-semibold text-rake">Rake</h3>
					<span class="status-badge {getStatusClass(health.rake_status)}">
						{health.rake_status.replace('_', ' ')}
					</span>
				</div>
				<div class="space-y-2">
					<div class="flex justify-between text-sm">
						<span class="text-forge-steel">Uptime</span>
						<span class="font-mono">{formatUptime(health.rake_uptime)}</span>
					</div>
					<div class="fc-progress-track fc-progress--rake">
						<div class="fc-progress-value" style="width: {health.rake_uptime}%"></div>
					</div>
				</div>
			</div>
		</div>

		<!-- Navigation Cards -->
		<div>
			<h2 class="text-2xl font-display font-semibold mb-4">Service Dashboards</h2>
			<div class="grid grid-cols-4 gap-6">
				<a href="/dataforge" class="nav-card dataforge">
					<h3 class="text-xl font-semibold text-dataforge mb-2">DataForge</h3>
					<p class="text-forge-steel text-sm">
						Vector search performance, query metrics, and storage analytics
					</p>
				</a>

				<a href="/neuroforge" class="nav-card neuroforge">
					<h3 class="text-xl font-semibold text-neuroforge mb-2">NeuroForge</h3>
					<p class="text-forge-steel text-sm">
						LLM usage, cost tracking, model performance, and token consumption
					</p>
				</a>

				<a href="/forgeagents" class="nav-card agents">
					<h3 class="text-xl font-semibold text-agents mb-2">ForgeAgents</h3>
					<p class="text-forge-steel text-sm">
						Agent orchestration, task execution, and performance monitoring
					</p>
				</a>

				<a href="/rake" class="nav-card rake">
					<h3 class="text-xl font-semibold text-rake mb-2">Rake</h3>
					<p class="text-forge-steel text-sm">
						Pipeline status, ingestion metrics, and data flow monitoring
					</p>
				</a>
			</div>
		</div>

		<!-- Recent Events -->
		<div>
			<h2 class="text-2xl font-display font-semibold mb-4">Recent Events</h2>
			<div class="panel">
				{#if recentEvents.length === 0}
					<p class="text-forge-steel text-center py-8">No events yet</p>
				{:else}
					<div class="space-y-2 fc-events">
						{#each recentEvents as event}
							<div class="fc-event-row fc-row-hoverable flex items-center justify-between py-2 border-b border-forge-steel/30 last:border-0">
								<div class="flex items-center space-x-4">
									<span class="w-2 h-2 rounded-full bg-{getServiceColor(event.service)}"></span>
									<span class="font-mono text-sm text-{getServiceColor(event.service)}">
										{event.service}
									</span>
									<span class="text-sm">{event.event_type}</span>
								</div>
								<div class="flex items-center space-x-4">
									<span class="status-badge {getStatusClass(event.severity === 'error' ? 'DOWN' : 'UP')} text-xs">
										{event.severity}
									</span>
									<span class="text-forge-steel text-sm font-mono">
										{formatTimestamp(event.timestamp)}
									</span>
								</div>
							</div>
						{/each}
					</div>
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
		background: rgba(0, 163, 255, 0.1);
		border: 1px solid rgba(0, 163, 255, 0.3);
		color: #00A3FF;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 500;
		transition: all 0.2s ease;
		cursor: pointer;
	}

	.export-button:hover {
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
