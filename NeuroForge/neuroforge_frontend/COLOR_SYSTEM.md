# NeuroForge Color System Implementation Guide

## Overview

This document describes the canonical color system for NeuroForge and provides implementation guidance for all frontend work.

## Core Brand Palette (NeuroForge Identity)

The NeuroForge tri-gradient is the visual signature of the application:

### Primary Colors

| Color            | Hex       | Tailwind                                  | Purpose                                                |
| ---------------- | --------- | ----------------------------------------- | ------------------------------------------------------ |
| **Ember Core**   | `#FF4C39` | `bg-nf-ember-core text-nf-ember-core`     | Primary CTAs, key highlights, focus states             |
| **Pulse Violet** | `#8A4FFF` | `bg-nf-pulse-violet text-nf-pulse-violet` | Secondary buttons, tags, selected states, glow effects |
| **Neural Blue**  | `#4DB2FF` | `bg-nf-neural-blue text-nf-neural-blue`   | Charts, routing lines, signals, data visualization     |

**Tri-Gradient (Hero Use Only):**

```
linear-gradient(135deg, #FF4C39 0%, #8A4FFF 50%, #4DB2FF 100%)
```

## Neutral & Base Palette (Dark-Mode First)

| Color       | Hex       | Tailwind               | Purpose                         |
| ----------- | --------- | ---------------------- | ------------------------------- |
| **Ash 950** | `#0C0C0E` | `bg-forge-ash-950`     | App background (outer shell)    |
| **Ash 900** | `#161618` | `bg-forge-ash-900`     | Primary surface (cards, panels) |
| **Ash 700** | `#2F2F33` | `border-forge-ash-700` | Borders, dividers               |
| **Ink**     | `#E7E7EF` | `text-forge-ink`       | Primary text (high contrast)    |
| **Ink Dim** | `#B5B7C3` | `text-forge-ink-dim`   | Secondary text, labels          |

## Status & Feedback Colors

| Color       | Hex       | Tailwind                        | Purpose                     |
| ----------- | --------- | ------------------------------- | --------------------------- |
| **Success** | `#2ECC71` | `bg-nf-success text-nf-success` | Positive states, completion |
| **Warning** | `#F1C40F` | `bg-nf-warning text-nf-warning` | Caution, attention needed   |
| **Danger**  | `#FF2E63` | `bg-nf-danger text-nf-danger`   | Errors, critical issues     |
| **Info**    | `#3FC9FF` | `bg-nf-info text-nf-info`       | Information, neutral states |

## Common Component Patterns

### Primary Button (CTA)

```svelte
<button class="bg-nf-ember-core text-white rounded-lg px-4 py-2 hover:opacity-90 transition">
  Action
</button>
```

### Secondary Button

```svelte
<button class="bg-nf-pulse-violet text-white rounded-lg px-4 py-2 hover:opacity-90 transition">
  Secondary
</button>
```

### Card / Surface

```svelte
<div class="rounded-lg border border-forge-ash-700 bg-forge-ash-900 p-6">
  <p class="text-forge-ink">Content</p>
</div>
```

### Status Badge

```svelte
<!-- Success -->
<span class="inline-flex rounded-full bg-nf-success/10 px-3 py-1 text-xs font-medium text-nf-success">
  Healthy
</span>

<!-- Warning -->
<span class="inline-flex rounded-full bg-nf-warning/10 px-3 py-1 text-xs font-medium text-nf-warning">
  Caution
</span>

<!-- Danger -->
<span class="inline-flex rounded-full bg-nf-danger/10 px-3 py-1 text-xs font-medium text-nf-danger">
  Failed
</span>
```

### Chart / Data Visualization

```svelte
<!-- Use Neural Blue for primary data -->
<div class="bg-nf-neural-blue rounded"></div>

<!-- Use Pulse Violet for secondary data -->
<div class="bg-nf-pulse-violet rounded"></div>

<!-- Use Ember Core for highlights -->
<div class="bg-nf-ember-core rounded"></div>
```

### Hero Header / Banner

```svelte
<div class="rounded-lg p-8" style="background: linear-gradient(135deg, #FF4C39 0%, #8A4FFF 50%, #4DB2FF 100%)">
  <h1 class="text-white text-2xl font-bold">Key Information</h1>
</div>
```

### Focus Ring / Glow Effect

```svelte
<input
  class="border border-forge-ash-700 bg-forge-ash-900 px-3 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-nf-pulse-violet"
/>
```

## Migration Guide

When updating existing code:

1. **Replace random colors** with semantic tokens

   - ❌ `bg-red-500` → ✅ `bg-nf-danger`
   - ❌ `text-blue-400` → ✅ `text-nf-neural-blue`

2. **Respect the hierarchy**

   - Primary actions: Ember Core
   - Secondary actions: Pulse Violet
   - Data/Signals: Neural Blue
   - Accents: Forge tokens

3. **Dark mode first**

   - Use `forge-ash-900` / `forge-ash-950` for surfaces
   - Use `forge-ink` / `forge-ink-dim` for text
   - Light mode is derived, not primary

4. **Keep meaning clear**
   - Never mix status colors in same small element
   - Status colors on neutral surfaces, not raw white
   - Use opacity for subtle variations (e.g., `bg-nf-success/10`)

## Tailwind Configuration

The colors are defined in `tailwind.config.ts`:

```typescript
theme: {
  extend: {
    colors: {
      'nf-ember-core': '#FF4C39',
      'nf-pulse-violet': '#8A4FFF',
      'nf-neural-blue': '#4DB2FF',
      'nf-success': '#2ECC71',
      'nf-warning': '#F1C40F',
      'nf-danger': '#FF2E63',
      'nf-info': '#3FC9FF',
      'forge-ash': { /* ... */ },
      'forge-ink': { /* ... */ },
    },
  },
}
```

## Examples

### Overview Dashboard

- Hero banner: Tri-gradient
- Stat cards: forge-ash-900 with forge-ink text
- Key metric highlights: nf-ember-core
- Trend indicator: nf-neural-blue

### Pipeline Visualizer

- Connections: nf-neural-blue
- Active nodes: nf-ember-core
- Background: forge-ash-900
- Text: forge-ink

### Model Evaluations

- Champion badge: nf-ember-core + emoji
- Score high (>0.9): nf-success
- Score medium (0.7-0.9): nf-warning
- Score low (<0.7): nf-danger
- Background: forge-ash-900

### Settings Panel

- Primary CTA: nf-ember-core
- Toggle on: nf-pulse-violet
- Section dividers: border-forge-ash-700
- Helper text: text-forge-ink-dim

## Accessibility Notes

- **Contrast**: All text colors meet WCAG AA standards on their background colors
- **Color blindness**: Don't rely on color alone - use icons, text labels, or patterns
- **Focus states**: Always provide visible focus indicators (ring or outline)
- **Dark mode**: Tested and optimized for dark-mode-first experience

## Reference

- **Color System Definition**: `src/lib/colors.ts`
- **Tailwind Config**: `tailwind.config.ts`
- **Current Pages**: All 10 pages in `/src/routes/` use this system
