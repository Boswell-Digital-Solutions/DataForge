/** @type {import('tailwindcss').Config} */
export default {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				// Forge brand colors
				'dataforge': '#00A3FF',      // Blue
				'neuroforge': '#A855F7',     // Violet
				'rake': '#2DD4BF',           // Cyan
				'forge-black': '#0D0D0F',    // Background
				'forge-slate': '#1A1A1D',    // Panels
				'forge-steel': '#4A4A4F',    // Borders/subtle
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
