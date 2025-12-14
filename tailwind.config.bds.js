// tailwind.config.js - VibeForge_BDS Enterprise Theme
// Version: 1.0
// Purpose: Complete design system for internal BDS engineering tools

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  darkMode: false, // Dark mode only - no toggle
  theme: {
    extend: {
      // ═══════════════════════════════════════════════════════════════
      // COLOR PALETTE - BDS Enterprise Theme
      // ═══════════════════════════════════════════════════════════════
      colors: {
        // Primary Colors
        'midnight': '#1B1E24',      // Dark background
        'brass': '#C19745',         // Primary action color
        'steel-blue': '#6A87A6',    // Secondary hierarchy
        
        // Secondary Colors
        'graphite': '#2A2D33',      // Mid-tone surfaces
        'cool-gray': '#8A8F99',     // Secondary text
        
        // Accent Colors
        'bds-violet': '#7B5FF1',    // Premium accent
        'success': '#49C883',       // Positive state
        'warning': '#E8A64D',       // Alert state
        'error': '#EF4444',         // Error state
        
        // Neutral Scale
        'off-white': '#F5F6F7',     // Primary text
        'disabled': '#555557',      // Disabled state
        
        // Transparent variants
        'brass-transparent': 'rgba(193, 151, 69, 0.1)',
        'border-light': 'rgba(255, 255, 255, 0.08)',
        'border-brass': 'rgba(193, 151, 69, 0.15)',
      },

      // ═══════════════════════════════════════════════════════════════
      // TYPOGRAPHY - Premium Font Stack
      // ═══════════════════════════════════════════════════════════════
      fontFamily: {
        'heading': ['Cinzel', 'serif'],     // Headings - Forge aesthetic
        'body': ['Inter', 'sans-serif'],    // Body text - clean, professional
        'mono': ['JetBrains Mono', 'monospace'], // Code, logs, technical
      },

      fontSize: {
        // Headings
        'h1': ['32px', { lineHeight: '1.2', letterSpacing: '0.5px' }],
        'h2': ['24px', { lineHeight: '1.3', letterSpacing: '0.4px' }],
        'h3': ['18px', { lineHeight: '1.4', letterSpacing: '0.3px' }],
        
        // Body
        'body': ['14px', { lineHeight: '1.5', letterSpacing: '0' }],
        'body-sm': ['12px', { lineHeight: '1.4', letterSpacing: '0' }],
        'caption': ['11px', { lineHeight: '1.4', letterSpacing: '0' }],
        
        // Code/Mono
        'code': ['13px', { lineHeight: '1.6', letterSpacing: '0.3px' }],
        'code-sm': ['12px', { lineHeight: '1.5', letterSpacing: '0.2px' }],
        'log': ['11px', { lineHeight: '1.6', letterSpacing: '0.3px' }],
      },

      fontWeight: {
        light: 300,
        normal: 400,
        medium: 500,
        semibold: 600,
        bold: 700,
      },

      letterSpacing: {
        tight: '-0.5px',
        normal: '0',
        wide: '0.3px',
        wider: '0.5px',
        widest: '1px',
      },

      // ═══════════════════════════════════════════════════════════════
      // SPACING - 8px Base Grid (Professional Tightness)
      // ═══════════════════════════════════════════════════════════════
      spacing: {
        'xs': '4px',    // Minimal gaps
        'sm': '8px',    // Component internal
        'md': '12px',   // Between elements
        'lg': '16px',   // Between sections
        'xl': '24px',   // Large gaps
        '2xl': '32px',  // Major separators
        // Sidebar
        'sidebar': '260px',
        'header': '56px',
      },

      gap: {
        'xs': '4px',
        'sm': '8px',
        'md': '12px',
        'lg': '16px',
        'xl': '24px',
      },

      padding: {
        'xs': '4px',
        'sm': '8px',
        'md': '12px',
        'lg': '16px',
        'xl': '24px',
      },

      margin: {
        'xs': '4px',
        'sm': '8px',
        'md': '12px',
        'lg': '16px',
        'xl': '24px',
      },

      // ═══════════════════════════════════════════════════════════════
      // BORDER RADIUS - Sharp, Professional
      // ═══════════════════════════════════════════════════════════════
      borderRadius: {
        none: '0',
        'xs': '2px',
        'sm': '4px',    // Default small
        'md': '6px',    // Panel default
        'lg': '8px',    // Large components
        'pill': '12px', // Badges, pills only
        'full': '9999px',
      },

      // ═══════════════════════════════════════════════════════════════
      // BORDERS - Subtle, Professional
      // ═══════════════════════════════════════════════════════════════
      borderWidth: {
        0: '0',
        1: '1px',
        2: '2px',
        4: '4px',
      },

      borderColor: {
        'light': 'rgba(255, 255, 255, 0.08)',
        'brass': 'rgba(193, 151, 69, 0.15)',
        'brass-light': 'rgba(193, 151, 69, 0.08)',
      },

      // ═══════════════════════════════════════════════════════════════
      // SHADOWS - Subtle, Professional
      // ═══════════════════════════════════════════════════════════════
      boxShadow: {
        none: 'none',
        'sm': '0 2px 4px rgba(0, 0, 0, 0.2)',
        'md': '0 4px 12px rgba(0, 0, 0, 0.25)',
        'lg': '0 8px 24px rgba(0, 0, 0, 0.3)',
        'brass-glow': '0 0 0 3px rgba(193, 151, 69, 0.1)',
        'focus': '0 0 0 3px rgba(193, 151, 69, 0.15)',
      },

      // ═══════════════════════════════════════════════════════════════
      // BACKGROUNDS - Gradients & Patterns (Minimal)
      // ═══════════════════════════════════════════════════════════════
      backgroundImage: {
        'brass-fade': 'linear-gradient(135deg, rgba(193, 151, 69, 0.05) 0%, rgba(193, 151, 69, 0) 100%)',
        'steel-fade': 'linear-gradient(135deg, rgba(106, 135, 166, 0.05) 0%, rgba(106, 135, 166, 0) 100%)',
        'violet-fade': 'linear-gradient(135deg, rgba(123, 95, 241, 0.05) 0%, rgba(123, 95, 241, 0) 100%)',
      },

      backgroundSize: {
        'metal': '64px 64px',
      },

      // ═══════════════════════════════════════════════════════════════
      // WIDTH & HEIGHT - Common Sizes
      // ═══════════════════════════════════════════════════════════════
      width: {
        'sidebar': '260px',
        'modal': '600px',
      },

      maxWidth: {
        'content': '1200px',
        'narrow': '900px',
      },

      height: {
        'header': '56px',
      },

      // ═══════════════════════════════════════════════════════════════
      // OPACITY - Controlled Transparency
      // ═══════════════════════════════════════════════════════════════
      opacity: {
        0: '0',
        5: '0.05',
        10: '0.1',
        15: '0.15',
        20: '0.2',
        25: '0.25',
        30: '0.3',
        40: '0.4',
        50: '0.5',
        60: '0.6',
        70: '0.7',
        75: '0.75',
        80: '0.8',
        90: '0.9',
        95: '0.95',
        100: '1',
      },

      // ═══════════════════════════════════════════════════════════════
      // TRANSITIONS - Subtle, Professional
      // ═══════════════════════════════════════════════════════════════
      transitionDuration: {
        0: '0ms',
        100: '100ms',
        150: '150ms',
        200: '200ms',
        300: '300ms',
      },

      transitionTimingFunction: {
        'ease': 'ease',
        'in': 'ease-in',
        'out': 'ease-out',
        'in-out': 'ease-in-out',
      },

      // ═══════════════════════════════════════════════════════════════
      // Z-INDEX - Layering
      // ═══════════════════════════════════════════════════════════════
      zIndex: {
        0: '0',
        10: '10',
        20: '20',
        30: '30',
        40: '40',
        50: '50',
        100: '100',
        1000: '1000',
      },
    },
  },

  // ═══════════════════════════════════════════════════════════════════════════
  // PLUGINS - Component Definitions
  // ═══════════════════════════════════════════════════════════════════════════
  plugins: [
    function ({ addComponents, theme }) {
      const components = {
        // ─────────────────────────────────────────────────────────────
        // BUTTONS
        // ─────────────────────────────────────────────────────────────
        '.btn': {
          '@apply': 'px-4 py-2.5 rounded-sm font-medium transition-all duration-150 cursor-pointer inline-flex items-center justify-center gap-2 text-sm whitespace-nowrap',
        },
        '.btn-primary': {
          '@apply': 'btn bg-brass text-midnight hover:bg-yellow-600 active:bg-yellow-700 disabled:bg-disabled disabled:text-cool-gray disabled:cursor-not-allowed',
          boxShadow: 'none',
          '&:hover:not(:disabled)': {
            boxShadow: '0 4px 12px rgba(193, 151, 69, 0.15)',
          },
        },
        '.btn-secondary': {
          '@apply': 'btn bg-transparent text-steel-blue border border-steel-blue hover:bg-opacity-10 hover:bg-steel-blue active:bg-opacity-20 disabled:text-disabled disabled:border-disabled',
        },
        '.btn-tertiary': {
          '@apply': 'btn bg-transparent text-cool-gray hover:text-brass disabled:text-disabled',
        },
        '.btn-icon': {
          '@apply': 'btn p-2 h-9 w-9',
        },

        // ─────────────────────────────────────────────────────────────
        // INPUT FIELDS
        // ─────────────────────────────────────────────────────────────
        '.input': {
          '@apply': 'px-3 py-2.5 rounded-sm bg-graphite text-off-white border border-border-light font-body text-sm transition-all duration-150',
          fontFamily: 'var(--font-body)',
          '&:focus': {
            '@apply': 'outline-none border-brass',
            boxShadow: 'var(--shadow-focus)',
          },
          '&:disabled': {
            '@apply': 'bg-midnight text-disabled cursor-not-allowed',
          },
          '&::placeholder': {
            '@apply': 'text-cool-gray',
          },
        },
        '.input-mono': {
          '@apply': 'input font-mono text-xs',
        },

        // ─────────────────────────────────────────────────────────────
        // CARDS & PANELS
        // ─────────────────────────────────────────────────────────────
        '.card': {
          '@apply': 'bg-graphite border border-border-light rounded-md p-4 mb-4',
        },
        '.panel': {
          '@apply': 'bg-graphite border border-border-light rounded-md overflow-hidden mb-4',
        },
        '.panel-header': {
          '@apply': 'flex items-center gap-2 px-4 py-3 border-b border-border-light bg-opacity-50 bg-brass-transparent',
        },
        '.panel-content': {
          '@apply': 'p-4 text-off-white text-sm',
        },

        // ─────────────────────────────────────────────────────────────
        // MODULE COMPONENTS
        // ─────────────────────────────────────────────────────────────
        '.module': {
          '@apply': 'bg-graphite border border-brass-light rounded-md overflow-hidden mb-4',
        },
        '.module-header': {
          '@apply': 'flex items-center gap-2 px-4 py-3 bg-brass-transparent border-b border-border-brass',
        },
        '.module-title': {
          '@apply': 'text-xs font-semibold text-brass uppercase tracking-wider',
        },
        '.module-id': {
          '@apply': 'ml-auto text-xs text-cool-gray font-mono tracking-wide',
        },
        '.module-content': {
          '@apply': 'p-4',
        },

        // ─────────────────────────────────────────────────────────────
        // BADGES & STATUS
        // ─────────────────────────────────────────────────────────────
        '.badge': {
          '@apply': 'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wider',
        },
        '.badge-success': {
          '@apply': 'badge bg-opacity-15 bg-success text-success border border-opacity-30 border-success',
        },
        '.badge-warning': {
          '@apply': 'badge bg-opacity-15 bg-warning text-warning border border-opacity-30 border-warning',
        },
        '.badge-error': {
          '@apply': 'badge bg-opacity-15 bg-error text-error border border-opacity-30 border-error',
        },
        '.badge-pending': {
          '@apply': 'badge bg-opacity-15 bg-steel-blue text-steel-blue border border-opacity-30 border-steel-blue',
        },
        '.badge-primary': {
          '@apply': 'badge bg-opacity-15 bg-brass text-brass border border-opacity-30 border-brass',
        },

        // ─────────────────────────────────────────────────────────────
        // CODE BLOCKS
        // ─────────────────────────────────────────────────────────────
        '.code-block': {
          '@apply': 'bg-midnight border border-border-light rounded-sm p-3 overflow-x-auto my-3 font-mono text-xs leading-relaxed text-off-white',
        },
        '.code-inline': {
          '@apply': 'bg-graphite px-1.5 py-0.5 rounded-xs font-mono text-xs text-bds-violet',
        },

        // ─────────────────────────────────────────────────────────────
        // TABLES
        // ─────────────────────────────────────────────────────────────
        '.table-container': {
          '@apply': 'w-full overflow-x-auto',
        },
        '.table': {
          '@apply': 'w-full text-sm border-collapse',
        },
        '.table-head': {
          '@apply': 'bg-brass-transparent border-b-2 border-border-brass',
        },
        '.table-header': {
          '@apply': 'px-3 py-3 text-left text-xs font-semibold text-brass uppercase tracking-wider',
        },
        '.table-body-row': {
          '@apply': 'border-b border-border-light transition-colors duration-150 hover:bg-brass-transparent',
        },
        '.table-cell': {
          '@apply': 'px-3 py-3 text-off-white',
        },
        '.table-cell-code': {
          '@apply': 'table-cell font-mono text-xs text-bds-violet',
        },

        // ─────────────────────────────────────────────────────────────
        // PROGRESS & INDICATORS
        // ─────────────────────────────────────────────────────────────
        '.progress': {
          '@apply': 'h-1.5 bg-border-light rounded-sm overflow-hidden my-2',
        },
        '.progress-fill': {
          '@apply': 'h-full bg-gradient-to-r from-brass to-bds-violet transition-all duration-300',
        },
        '.progress-success .progress-fill': {
          '@apply': 'from-success to-success',
        },
        '.progress-warning .progress-fill': {
          '@apply': 'from-warning to-warning',
        },
        '.progress-error .progress-fill': {
          '@apply': 'from-error to-error',
        },

        // ─────────────────────────────────────────────────────────────
        // LAYOUT UTILITIES
        // ─────────────────────────────────────────────────────────────
        '.sidebar': {
          '@apply': 'w-sidebar bg-midnight border-r border-border-brass fixed left-0 top-0 h-screen overflow-y-auto',
        },
        '.main-content': {
          '@apply': 'ml-sidebar',
        },
        '.header': {
          '@apply': 'h-header bg-midnight border-b border-border-brass sticky top-0 z-100',
        },
        '.container-x': {
          '@apply': 'mx-auto max-w-content px-6',
        },

        // ─────────────────────────────────────────────────────────────
        // TEXT UTILITIES
        // ─────────────────────────────────────────────────────────────
        '.text-primary': {
          '@apply': 'text-off-white',
        },
        '.text-secondary': {
          '@apply': 'text-cool-gray',
        },
        '.text-tertiary': {
          '@apply': 'text-opacity-60 text-cool-gray',
        },
        '.text-disabled': {
          '@apply': 'text-disabled',
        },
        '.text-accent': {
          '@apply': 'text-brass',
        },
        '.text-success': {
          '@apply': 'text-success',
        },
        '.text-warning': {
          '@apply': 'text-warning',
        },
        '.text-error': {
          '@apply': 'text-error',
        },

        // ─────────────────────────────────────────────────────────────
        // HEADINGS
        // ─────────────────────────────────────────────────────────────
        '.heading-1': {
          '@apply': 'text-3xl font-heading font-light text-off-white tracking-wider',
        },
        '.heading-2': {
          '@apply': 'text-2xl font-heading font-light text-off-white tracking-wide',
        },
        '.heading-3': {
          '@apply': 'text-lg font-heading font-light text-off-white tracking-wide',
        },
        '.heading-sm': {
          '@apply': 'text-sm font-semibold text-off-white uppercase tracking-wider',
        },
      };

      addComponents(components);
    },
  ],
};
