# VibeForge_BDS — Quick Reference Card

**Print this, laminate it, keep it at your desk while building** 📋

---

## 🎨 COLOR PALETTE

### Primary
```
Midnight Slate    #1B1E24   RGB: 27, 30, 36      [Primary background]
Forge Brass       #C19745   RGB: 193, 151, 69    [Action, accents]
Steel Blue        #6A87A6   RGB: 106, 135, 166   [Secondary]
```

### Secondary
```
Graphite Gray     #2A2D33   RGB: 42, 45, 51      [Panel backgrounds]
Cool Gray         #8A8F99   RGB: 138, 143, 153   [Secondary text]
```

### Accent
```
BDS Violet        #7B5FF1   RGB: 123, 95, 241    [Premium accent]
Success Green     #49C883   RGB: 73, 200, 131    [Success state]
Warning Amber     #E8A64D   RGB: 232, 166, 77    [Warning state]
Error Red         #EF4444   RGB: 239, 68, 68     [Error state]
```

### Neutral
```
Off-White         #F5F6F7   [Primary text]
White             #FFFFFF   [High contrast]
Disabled Gray     #555557   [Disabled state]
Border Light      rgba(255,255,255,0.08)   [Subtle dividers]
Border Brass      rgba(193,151,69,0.15)    [Accent borders]
```

---

## 🖋️ TYPOGRAPHY

### Font Families
```
Headings:   font-family: 'Cinzel', serif
            font-weight: 300 (Light)
            letter-spacing: 0.5px
            ↳ Premium, Forge aesthetic

Body:       font-family: 'Inter', sans-serif
            font-weight: 400-600
            line-height: 1.5
            ↳ Clean, professional, readable

Code/Logs:  font-family: 'JetBrains Mono', monospace
            font-weight: 400-700
            font-size: 11-13px
            letter-spacing: 0.3px
            ↳ Technical, precise
```

### Type Scale
```
H1    32px   Light    1.2 line-height    0.5px letter-spacing
H2    24px   Light    1.3 line-height    0.4px letter-spacing
H3    18px   Light    1.4 line-height    0.3px letter-spacing
Body  14px   Regular  1.5 line-height
Body  12px   Regular  1.4 line-height
Code  13px   Regular  1.6 line-height
Logs  11px   Regular  1.6 line-height
```

---

## 📏 SPACING GRID (8px Base)

```
--spacing-xs:   4px     Minimal gaps
--spacing-sm:   8px     Component internal
--spacing-md:  12px     Between elements (DEFAULT)
--spacing-lg:  16px     Between sections
--spacing-xl:  24px     Large gaps
--spacing-2xl: 32px     Major separators

RULE: Always use multiples of 4px
      Avoid: 5px, 7px, 11px, 13px, 15px, etc.
```

---

## 🔲 COMPONENT SIZING

### Buttons
```
Small:    font-size 12px   padding 8px 12px     height 32px
Default:  font-size 14px   padding 10px 16px    height 40px
Large:    font-size 16px   padding 12px 20px    height 48px

Border-radius: 4px (sharp, not rounded)
```

### Inputs
```
Height: 40px
Padding: 10px 12px
Border-radius: 4px
Focus border: var(--brass) with glow shadow
Focus shadow: 0 0 0 3px rgba(193, 151, 69, 0.1)
```

### Panels & Cards
```
Border-radius: 6px
Border: 1px solid rgba(255, 255, 255, 0.08)
Padding: 16px
Background: var(--graphite)
```

### Sidebar
```
Width: 260px
Position: fixed left 0 top 0
Height: 100vh
Background: var(--midnight)
Border-right: 1px solid rgba(193, 151, 69, 0.15)
```

### Header
```
Height: 56px
Position: sticky top 0
Background: var(--midnight)
Border-bottom: 1px solid rgba(193, 151, 69, 0.15)
Margin-left: 260px (account for sidebar)
```

---

## 🎛️ COMMON TAILWIND CLASSES

### Colors
```
bg-midnight       → Dark background
bg-graphite       → Panel/card background
bg-brass-transparent → Brass with 5-10% opacity
text-off-white    → Primary text
text-brass        → Accent text
text-cool-gray    → Secondary text
border-border-light  → Subtle border
border-border-brass  → Accent border
```

### Spacing
```
p-md   → padding: 12px
m-lg   → margin: 16px
gap-sm → gap: 8px
gap-md → gap: 12px (default)
```

### Typography
```
text-h1       → 32px Cinzel Light
text-h2       → 24px Cinzel Light
text-body     → 14px Inter Regular
text-caption  → 11px Inter
font-mono     → JetBrains Mono
code-inline   → Inline code styling
```

### Buttons
```
btn btn-primary      → Brass background, midnight text
btn btn-secondary    → Transparent, steel-blue border
btn btn-tertiary     → Transparent, cool-gray text
```

### Panels & Cards
```
card        → Basic card (padding, border, background)
panel       → Card with header section
module      → Panel with brass accent header
panel-header → Title bar with border
panel-content → Interior content area
```

### Badges
```
badge badge-success   → Green background, 15% opacity
badge badge-warning   → Amber background, 15% opacity
badge badge-error     → Red background, 15% opacity
badge badge-pending   → Steel-blue background, 15% opacity
```

### Tables
```
table              → Base table styling
table-head         → Header row (brass-transparent bg)
table-header       → Header cell (brass text, uppercase)
table-body-row     → Data row (hover effect)
table-cell         → Data cell
table-cell-code    → Code-style cell (monospace, violet)
```

---

## 🔨 DO's & DON'Ts

### ✅ DO THIS
```
Border-radius:     4px, 6px, 8px (use these only)
Spacing:           12px, 16px, 24px (multiples of 4)
Shadows:           sm, md, lg (use provided ones)
Colors:            Use --var names (not hardcoded hex)
Typography:        Use type scale classes (not custom px)
```

### ❌ DON'T DO THIS
```
Border-radius:     7px, 10px, 11px (inconsistent)
Spacing:           13px, 15px, 18px (off-grid)
Shadows:           Custom shadows (use provided)
Colors:            Hardcode #FF00FF or rgba()
Typography:        random font-size (use scale)
Light mode:        It doesn't exist (dark only)
Rounded buttons:   Use 4px radius, not 12px
```

---

## 🏗️ COMPONENT PATTERNS

### Button
```svelte
<Button variant="primary">Click me</Button>
<Button variant="secondary">Secondary</Button>
<Button variant="tertiary">Tertiary</Button>
<Button variant="primary" disabled>Disabled</Button>
```

### Input
```svelte
<Input label="Full Name" placeholder="Your name" />
<Input label="API Key" type="password" />
<Input label="Code" monospace={true} />
<Input label="Name" error="This field is required" />
```

### Panel
```svelte
<Panel title="Settings" subtitle="Configure your workspace" icon="⚙️">
  <!-- content -->
</Panel>
```

### Badge
```svelte
<span class="badge badge-success">Active</span>
<span class="badge badge-warning">Pending</span>
<span class="badge badge-error">Failed</span>
<span class="badge badge-pending">In Progress</span>
```

### Table
```svelte
<table class="table">
  <thead class="table-head">
    <tr><th class="table-header">Column Name</th></tr>
  </thead>
  <tbody>
    <tr class="table-body-row">
      <td class="table-cell">Data</td>
    </tr>
  </tbody>
</table>
```

---

## 📐 LAYOUT STRUCTURE

```
┌─────────────────────────────────────────────────────┐
│ SIDEBAR (260px)  │ HEADER (56px height)             │
│ fixed left       │ sticky top                        │
│                  ├──────────────────────────────────┤
│                  │ MAIN CONTENT                     │
│  Dashboard       │ padding: 24px                    │
│  Skills Lib      │ margin-left: 260px               │
│  Planning        │ max-width: 1200px                │
│  Execution       │                                  │
│  Evaluation      │ [Dashboard Panels]               │
│  Coordination    │ [Module Components]              │
│  System Logs     │ [Tables & Metrics]               │
│  Settings        │                                  │
│                  │                                  │
└─────────────────────────────────────────────────────┘
```

---

## 🎬 IDENTITY BADGES (Always Visible)

```
Header (top-right):
┌─────────────────────┐
│ charles@bds.com     │
│ Agents: 120 Active  │
│ BDS Edition v1.0.0  │
│ SAS: ON ●           │
└─────────────────────┘

Watermark (bottom-right, faint):
Boswell Digital Solutions LLC • Internal Build

Sidebar (header):
VibeForge_BDS
[INTERNAL • BDS ENGINEERING pill]

Panels (each module):
⚙️ MODULE NAME       [MOD-ID]
```

---

## ⚡ QUICK MIGRATION GUIDE

### From Public VibeForge to VibeForge_BDS

```
OLD CLASS                          → NEW CLASS
────────────────────────────────────────────────────
bg-gradient-to-br from-violet-*    → bg-graphite border border-border-light
border-violet-500                  → border-border-brass
text-violet-300                    → text-brass
rounded-lg (12px)                  → rounded-md (6px)
px-6 py-4                          → px-4 py-3
gap-6                              → gap-4
bg-slate-800                       → bg-graphite
text-slate-300                     → text-cool-gray
shadow-lg                          → shadow-md
```

---

## 📋 IMPLEMENTATION CHECKLIST

### Phase 1: Fonts & Config
- [ ] Download fonts (Cinzel, Inter, JetBrains Mono)
- [ ] Copy to static/fonts/
- [ ] Create fonts.css import
- [ ] Update app.css with root variables
- [ ] Replace tailwind.config.js
- [ ] Test: npm run build

### Phase 2: Layout
- [ ] Create Sidebar.svelte
- [ ] Create Header.svelte
- [ ] Update +layout.svelte
- [ ] Test sidebar & header rendering

### Phase 3: Components
- [ ] Create Button.svelte
- [ ] Create Input.svelte
- [ ] Create Panel.svelte
- [ ] Test component variants

### Phase 4: Pages
- [ ] Update colors across dashboard
- [ ] Update spacing (gap-lg → gap-md)
- [ ] Update border-radius (rounded-lg → rounded-md)
- [ ] Test each page visually

### Phase 5: Polish
- [ ] Visual review (colors, spacing, borders)
- [ ] Cross-browser test
- [ ] Accessibility check (contrast, focus)
- [ ] Performance optimization

---

## 🔗 DOCUMENT REFERENCES

| Document | Purpose | Read Time |
|----------|---------|-----------|
| VIBEFORGE_BDS_DESIGN_SYSTEM.md | Complete spec (15 sections) | 30 min |
| tailwind.config.bds.js | Tailwind config (drop-in) | 5 min |
| VIBEFORGE_BDS_IMPLEMENTATION_GUIDE.md | Step-by-step (6 phases) | 15 min |
| VIBEFORGE_BDS_BRANDING_SUMMARY.md | Executive overview | 10 min |
| THIS CARD | Quick reference | 2 min |

---

**Print & Laminate This Card** 📌

Keep it at your desk while implementing. Reference it during code review.
All color values, spacing rules, and component patterns in one place.

---

**Version:** 1.0  
**Status:** Ready for Production  
**Last Updated:** December 8, 2025  
**Built by:** Boswell Digital Solutions LLC
