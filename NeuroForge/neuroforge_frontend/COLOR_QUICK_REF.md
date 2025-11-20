# NeuroForge Color System - Quick Reference

## 🎨 The Tri-Gradient (Brand Identity)

```
#FF4C39 (Ember) → #8A4FFF (Violet) → #4DB2FF (Blue)
```

## 🔴 Primary Colors (Use These!)

| Name         | Hex     | Tailwind          | Use For                                      |
| ------------ | ------- | ----------------- | -------------------------------------------- |
| Ember Core   | #FF4C39 | `nf-ember-core`   | **CTAs, primary buttons, key highlights**    |
| Pulse Violet | #8A4FFF | `nf-pulse-violet` | **Secondary buttons, tags, selected states** |
| Neural Blue  | #4DB2FF | `nf-neural-blue`  | **Charts, data, signals, routing**           |

## 🎭 Status Colors

| Name    | Hex     | Tailwind     | When                  |
| ------- | ------- | ------------ | --------------------- |
| Success | #2ECC71 | `nf-success` | ✅ Healthy, completed |
| Warning | #F1C40F | `nf-warning` | ⚠️ Needs attention    |
| Danger  | #FF2E63 | `nf-danger`  | ❌ Error, critical    |
| Info    | #3FC9FF | `nf-info`    | ℹ️ Informational      |

## 🖤 Neutrals (Dark-First)

| Name    | Hex     | Tailwind        | Use For                 |
| ------- | ------- | --------------- | ----------------------- |
| Ash 950 | #0C0C0E | `forge-ash-950` | App background          |
| Ash 900 | #161618 | `forge-ash-900` | Cards, panels, surfaces |
| Ash 700 | #2F2F33 | `forge-ash-700` | Borders, dividers       |
| Ink     | #E7E7EF | `forge-ink`     | Primary text            |
| Ink Dim | #B5B7C3 | `forge-ink-dim` | Secondary text          |

## ⚡ Quick Examples

### Primary Button

```html
<button class="bg-nf-ember-core text-white rounded px-4 py-2">Click Me</button>
```

### Card

```html
<div class="bg-forge-ash-900 border border-forge-ash-700 rounded-lg p-6">
  <p class="text-forge-ink">Content here</p>
</div>
```

### Status Badge (Success)

```html
<span
  class="bg-nf-success/10 text-nf-success px-3 py-1 rounded-full text-xs font-medium"
>
  ✓ Healthy
</span>
```

### Hero Banner

```html
<div
  style="background: linear-gradient(135deg, #FF4C39 0%, #8A4FFF 50%, #4DB2FF 100%)"
>
  <h1 class="text-white">Title</h1>
</div>
```

## 📋 Rules

✅ **DO:**

- Use semantic token names (`nf-ember-core`, not `#FF4C39`)
- Default CTAs to Ember Core
- Use Neural Blue for data/charts
- Use status colors for feedback
- Dark backgrounds + light text

❌ **DON'T:**

- Mix random colors
- Use light mode as primary
- Combine two brand colors in same small element
- Status colors on white backgrounds
- Hex codes in components (use tokens!)

## 📖 Full Reference

See `COLOR_SYSTEM.md` for complete guide with accessibility notes and migration patterns.
