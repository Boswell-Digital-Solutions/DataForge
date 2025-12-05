/** @type {import('tailwindcss').Config} */
export default {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				// Forge brand colors (CANONICAL - from design system)
				'dataforge': '#0094E8',      // Blue - memory / vector search
				'neuroforge': '#9B4DE8',     // Violet - AI orchestration
				'rake': '#22CFC5',           // Cyan/Teal - ingestion pipeline
				'agents': '#F59E0B',         // Amber - agent orchestration
				'forge-black': '#0B0C0E',    // Background
				'forge-slate': '#1E2025',    // Panels/Surface
				'forge-steel': '#BFC2C5',    // Muted text
				'forge-ember': '#D97706',    // Accent/alerts
			},
			fontFamily: {
				sans: ['Inter', 'system-ui', 'sans-serif'],
				display: ['Cinzel', 'serif'],
				mono: ['JetBrains Mono', 'monospace'],
			},
		},
	},
	plugins: [],
};
