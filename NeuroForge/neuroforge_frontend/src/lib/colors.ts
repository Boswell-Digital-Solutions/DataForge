/**
 * NeuroForge Color System
 * Canonical color palette and design tokens
 * This is the authoritative reference for all UI work in NeuroForge
 */

// ============================================================================
// Core Brand Palette - NeuroForge Identity (Tri-Gradient)
// ============================================================================

export const NF_COLORS = {
  // Primary Accents
  emberCore: "#FF4C39", // Primary accent - CTAs, key highlights, focus states
  pulseViolet: "#8A4FFF", // Secondary accent - secondary buttons, tags, selected states
  neuralBlue: "#4DB2FF", // Tertiary accent - charts, routing lines, signals

  // Gradients
  triGradient: "linear-gradient(135deg, #FF4C39 0%, #8A4FFF 50%, #4DB2FF 100%)",
  circuitBar: "linear-gradient(90deg, #FF4C39 0%, #4DB2FF 100%)",
  aetherPulse:
    "0 0 0 1px rgba(138, 79, 255, 0.2), 0 0 24px rgba(77, 178, 255, 0.2)",

  // Status / Feedback Colors
  success: "#2ECC71",
  warning: "#F1C40F",
  danger: "#FF2E63",
  info: "#3FC9FF",
};

// ============================================================================
// Neutral & Base Palette (Forge-Wide, Dark-Mode First)
// ============================================================================

export const FORGE_NEUTRALS = {
  // Ash / Gray scale
  ash950: "#0C0C0E", // App background (dark mode), outer shell
  ash900: "#161618", // Primary surface (cards, panels, rails)
  ash700: "#2F2F33", // Borders, dividers, muted containers

  // Ink / Text
  ink: "#E7E7EF", // Primary text
  inkDim: "#B5B7C3", // Secondary text, labels, helper text
};

// ============================================================================
// Tailwind Config Reference
// ============================================================================

/*
Add to tailwind.config.ts:

theme: {
  extend: {
    colors: {
      // NeuroForge Brand
      'nf-ember-core': '#FF4C39',
      'nf-pulse-violet': '#8A4FFF',
      'nf-neural-blue': '#4DB2FF',
      'nf-success': '#2ECC71',
      'nf-warning': '#F1C40F',
      'nf-danger': '#FF2E63',
      'nf-info': '#3FC9FF',

      // Forge Neutrals
      'forge-ash': {
        950: '#0C0C0E',
        900: '#161618',
        700: '#2F2F33',
      },
      'forge-ink': '#E7E7EF',
      'forge-ink-dim': '#B5B7C3',
    },
  },
}
*/

// ============================================================================
// Usage Rules for Claude
// ============================================================================

/*
✅ Dark Mode First (Primary)
- Use forge-ash-950 / forge-ash-900 for backgrounds and cards
- Use forge-ink / forge-ink-dim for text
- Use nf-ember-core, nf-pulse-violet, nf-neural-blue for accents

✅ Component Hierarchy
- CTAs & Primary Actions: nf-ember-core (#FF4C39)
- Secondary Actions: nf-pulse-violet (#8A4FFF)
- Charts, Routing, Neural Flows: nf-neural-blue (#4DB2FF)
- Hero Headers, Main Banners, Pipeline Diagrams: Use tri-gradient (sparingly)

✅ Status Indicators
- Success: #2ECC71 (on neutral surfaces, never raw white)
- Warning: #F1C40F
- Danger: #FF2E63
- Info: #3FC9FF
- Keep clear meaning - avoid mixing with brand accents in same element

✅ When to Migrate
- Existing code using random colors should migrate to this system
- Keep consistency - don't mix systems
- Use semantic token names (bg-nf-ember-core) not hex codes (#FF4C39)

✅ Special Effects
- Focus rings: box-shadow with nf-pulse-violet or nf-neural-blue
- Glows: Use aetherPulse pattern for soft, sophisticated look
- Gradients: Reserve tri-gradient for high-impact hero moments
*/

export default NF_COLORS;
