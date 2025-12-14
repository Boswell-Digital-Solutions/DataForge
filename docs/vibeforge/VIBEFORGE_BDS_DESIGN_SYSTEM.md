# VibeForge_BDS Design System v1.0

**Version:** 1.0  
**Date:** December 8, 2025  
**Purpose:** Internal (BDS Engineering) visual identity & UX standards  
**Status:** Ready for Implementation  

---

## 🎯 Design Philosophy

**VibeForge_BDS is VibeForge wearing a suit.**

Same powerful foundation, elevated presentation. Less playful, more professional. Optimized for long dev sessions, serious automation, compliance tracking. Signals internal authority without sacrificing usability.

**Key Principle:** Professional ≠ Boring. Enterprise ≠ Cold.

---

## 1. Color Palette

### 1.1 Primary Colors

| Name | Hex | RGB | Purpose | Usage |
|------|-----|-----|---------|-------|
| **Midnight Slate** | `#1B1E24` | 27, 30, 36 | Background, dark panels | Primary bg, deep wells |
| **Forge Brass (Muted)** | `#C19745` | 193, 151, 69 | Primary action, hierarchy | Accents, borders, highlights |
| **Steel Blue** | `#6A87A6` | 106, 135, 166 | Secondary hierarchy | Section headers, secondary CTAs |

### 1.2 Secondary Colors

| Name | Hex | RGB | Purpose | Usage |
|------|-----|-----|---------|-------|
| **Graphite Gray** | `#2A2D33` | 42, 45, 51 | Mid-tone surfaces | Panels, cards, container bg |
| **Cool Gray** | `#8A8F99` | 138, 143, 153 | Text secondary, disabled | Labels, hints, secondary text |

### 1.3 Accent Colors

| Name | Hex | RGB | Purpose | Usage |
|------|-----|-----|---------|-------|
| **BDS Internal Violet** | `#7B5FF1` | 123, 95, 241 | Premium accent | Agent modules, special UI |
| **Success Green** | `#49C883` | 73, 200, 131 | Positive state | Success, compliance pass |
| **Warning Amber** | `#E8A64D` | 232, 166, 77 | Alert state | Warnings, pending approvals |
| **Error Red** | `#EF4444` | 239, 68, 68 | Error state | Failures, rollbacks, violations |

### 1.4 Neutral Scale

| Name | Hex | Purpose |
|------|-----|---------|
| **White** | `#FFFFFF` | Text on dark, highest contrast |
| **Off-White** | `#F5F6F7` | Light text on Midnight Slate |
| **Border Gray** | `rgba(255,255,255,0.08)` | Subtle dividers |
| **Disabled Gray** | `#555557` | Disabled states |

---

## 2. Typography

### 2.1 Font Stack

```css
/* Headings & Titles */
font-family: 'Cinzel', serif;
font-weight: 300 (Light);
letter-spacing: 0.5px;
/* Forge aesthetic, premium feel */

/* Body & UI */
font-family: 'Inter', sans-serif;
font-weight: 400-500;
line-height: 1.5;
/* Clean, professional, readable */

/* Code, Logs, Tokens */
font-family: 'JetBrains Mono', monospace;
font-weight: 400;
font-size: 12px-13px;
letter-spacing: 0.3px;
/* Technical, precise, developer-focused */
```

### 2.2 Type Scale

| Element | Font | Size | Weight | Line-Height | Letter-Spacing |
|---------|------|------|--------|-------------|-----------------|
| **H1** (Page Title) | Cinzel | 32px | Light | 1.2 | 0.5px |
| **H2** (Section) | Cinzel | 24px | Light | 1.3 | 0.4px |
| **H3** (Subsection) | Cinzel | 18px | Light | 1.4 | 0.3px |
| **Body** (Default) | Inter | 14px | 400 | 1.5 | 0 |
| **Body Small** | Inter | 12px | 400 | 1.4 | 0 |
| **Caption** | Inter | 11px | 400 | 1.4 | 0 |
| **Code Block** | JetBrains Mono | 13px | 400 | 1.6 | 0.3px |
| **Code Inline** | JetBrains Mono | 12px | 400 | 1.5 | 0.2px |
| **Logs** | JetBrains Mono | 11px | 400 | 1.6 | 0.3px |

### 2.3 Text Colors

| Usage | Color | Hex |
|-------|-------|-----|
| **Primary Text** | Off-White | `#F5F6F7` |
| **Secondary Text** | Cool Gray | `#8A8F99` |
| **Tertiary Text** | Cool Gray (60% opacity) | `rgba(138,143,153,0.6)` |
| **Disabled Text** | Disabled Gray | `#555557` |
| **Accent Text** | Forge Brass | `#C19745` |
| **Code Text** | Off-White | `#F5F6F7` |

---

## 3. Layout & Spacing

### 3.1 Content Width

| Context | Width | Notes |
|---------|-------|-------|
| **Max Content Width** | 1200px | Main dashboard, reports |
| **Sidebar Width** | 260px | Fixed left sidebar |
| **Modal Width** | 600px | Standard dialogs |
| **Code Panel** | 100% (minus sidebar) | Console, logs, output |

### 3.2 Spacing Scale

```css
/* Tight, professional spacing */
--spacing-xs: 4px;      /* Minimal gaps */
--spacing-sm: 8px;      /* Component internal */
--spacing-md: 12px;     /* Between elements */
--spacing-lg: 16px;     /* Between sections */
--spacing-xl: 24px;     /* Large gaps */
--spacing-2xl: 32px;    /* Major separators */

/* BDS Standard: Use md/lg more than xl */
/* Never use 20px or 28px (in-between mess) */
```

### 3.3 Grid & Rhythm

```css
/* 8px base grid */
margin: 12px 16px;      /* Always multiples of 4px */
padding: 12px;          /* Consistent insets */
gap: 12px;              /* Component spacing */
border-radius: 4px;     /* Sharp, professional */
```

---

## 4. Component Styling

### 4.1 Buttons

**Primary Button (Brass Action)**

```css
background: #C19745;
color: #1B1E24;
padding: 10px 16px;
border-radius: 4px;
font-weight: 500;
border: none;
cursor: pointer;

&:hover {
  background: #D4A859;
  box-shadow: 0 4px 12px rgba(193, 151, 69, 0.15);
}

&:active {
  background: #B08840;
}

&:disabled {
  background: #555557;
  color: #8A8F99;
  cursor: not-allowed;
}
```

**Secondary Button (Steel Blue)**

```css
background: transparent;
color: #6A87A6;
border: 1px solid #6A87A6;
padding: 10px 16px;
border-radius: 4px;
font-weight: 500;

&:hover {
  background: rgba(106, 135, 166, 0.1);
  border-color: #7B92B1;
}
```

**Tertiary Button (Gray)**

```css
background: transparent;
color: #8A8F99;
border: none;
padding: 10px 16px;
font-weight: 400;

&:hover {
  color: #C19745;
}
```

### 4.2 Input Fields

```css
input, textarea, select {
  background: #2A2D33;
  color: #F5F6F7;
  border: 1px solid rgba(255, 255, 255, 0.12);
  padding: 10px 12px;
  border-radius: 4px;
  font-family: 'Inter', sans-serif;
  font-size: 14px;
  line-height: 1.5;

  &:focus {
    outline: none;
    border-color: #C19745;
    box-shadow: 0 0 0 3px rgba(193, 151, 69, 0.1);
  }

  &:disabled {
    background: #1B1E24;
    color: #555557;
  }

  &::placeholder {
    color: #8A8F99;
  }
}
```

### 4.3 Cards & Panels

```css
.panel {
  background: #2A2D33;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 16px;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  margin-bottom: 12px;
}

.panel-title {
  font-size: 16px;
  font-weight: 500;
  color: #F5F6F7;
}

.panel-subtitle {
  font-size: 12px;
  color: #8A8F99;
}
```

### 4.4 Tables

```css
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

thead {
  background: rgba(193, 151, 69, 0.05);
  border-bottom: 2px solid rgba(193, 151, 69, 0.2);
}

th {
  padding: 12px;
  text-align: left;
  color: #C19745;
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

tbody tr {
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  transition: background-color 0.15s;

  &:hover {
    background: rgba(193, 151, 69, 0.03);
  }
}

td {
  padding: 12px;
  color: #F5F6F7;
  font-family: 'Inter', sans-serif;

  &.code {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: #7B5FF1;
  }
}
```

### 4.5 Status Badges

```css
.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.badge-success {
  background: rgba(73, 200, 131, 0.15);
  color: #49C883;
  border: 1px solid rgba(73, 200, 131, 0.3);
}

.badge-warning {
  background: rgba(232, 166, 77, 0.15);
  color: #E8A64D;
  border: 1px solid rgba(232, 166, 77, 0.3);
}

.badge-error {
  background: rgba(239, 68, 68, 0.15);
  color: #EF4444;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.badge-pending {
  background: rgba(106, 135, 166, 0.15);
  color: #6A87A6;
  border: 1px solid rgba(106, 135, 166, 0.3);
}
```

### 4.6 Progress Bars

```css
.progress {
  height: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  overflow: hidden;
  margin: 8px 0;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #C19745, #7B5FF1);
  transition: width 0.3s ease;
}

.progress.success .progress-fill {
  background: #49C883;
}

.progress.warning .progress-fill {
  background: #E8A64D;
}

.progress.error .progress-fill {
  background: #EF4444;
}
```

---

## 5. Navigation & Sidebar

### 5.1 Sidebar Structure

```
┌─────────────────────────┐
│  VibeForge_BDS          │ ← Header
├─────────────────────────┤
│                         │
│  📊 Dashboard           │
│  📚 Skills Library      │
│  🧠 Planning            │
│  ⚙️  Execution          │
│  ✓  Evaluation          │
│  🔗 Coordination        │
│  📋 System Logs         │
│  ⚙️  BDS Settings       │
│                         │
├─────────────────────────┤
│  charles@bds            │ ← Status
│  120 Skills Active      │
│  SAS: ON ●              │
└─────────────────────────┘
```

### 5.2 Sidebar Styling

```css
.sidebar {
  width: 260px;
  background: #1B1E24;
  border-right: 1px solid rgba(193, 151, 69, 0.15);
  padding: 16px 0;
  position: fixed;
  left: 0;
  top: 0;
  height: 100vh;
  overflow-y: auto;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  margin-bottom: 12px;
}

.sidebar-logo {
  font-family: 'Cinzel', serif;
  font-size: 18px;
  font-weight: 300;
  color: #C19745;
  letter-spacing: 0.5px;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 0 8px;
}

.sidebar-nav-item {
  padding: 10px 12px;
  color: #8A8F99;
  border-left: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;

  &:hover {
    color: #C19745;
    background: rgba(193, 151, 69, 0.08);
    border-left-color: #C19745;
  }

  &.active {
    color: #C19745;
    background: rgba(193, 151, 69, 0.1);
    border-left-color: #C19745;
    font-weight: 500;
  }
}

.sidebar-footer {
  position: absolute;
  bottom: 16px;
  left: 0;
  right: 0;
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  text-align: center;
}

.sidebar-status {
  font-size: 11px;
  color: #8A8F99;
  line-height: 1.6;
}

.status-indicator {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #49C883;
  margin-right: 4px;
}
```

---

## 6. Header & Top Navigation

```css
.header {
  height: 56px;
  background: #1B1E24;
  border-bottom: 1px solid rgba(193, 151, 69, 0.15);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  margin-left: 260px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-title {
  font-family: 'Cinzel', serif;
  font-size: 16px;
  font-weight: 300;
  color: #C19745;
  letter-spacing: 0.5px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header-user {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: #8A8F99;
}

.header-badge {
  background: #2A2D33;
  border: 1px solid rgba(193, 151, 69, 0.2);
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  color: #C19745;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.sas-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #8A8F99;

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #49C883; /* Green when ON */
  }
}
```

---

## 7. Identity Elements

### 7.1 BDS Edition Badge

```css
.bds-badge {
  position: fixed;
  top: 16px;
  right: 16px;
  background: #2A2D33;
  border: 1px solid rgba(193, 151, 69, 0.3);
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  color: #C19745;
  z-index: 1000;
}
```

### 7.2 Internal Watermark

```css
.watermark {
  position: fixed;
  bottom: 16px;
  right: 16px;
  font-size: 9px;
  color: rgba(193, 151, 69, 0.15);
  font-family: 'Inter', sans-serif;
  text-align: right;
  pointer-events: none;
  z-index: 1;
}
```

### 7.3 Internal Identity Pill

```css
.bds-identity {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #2A2D33;
  color: #C19745;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  border: 1px solid rgba(193, 151, 69, 0.2);

  &::before {
    content: '';
    display: inline-block;
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: #C19745;
  }
}
```

### 7.4 Skill Count Badge

```css
.skill-badge {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 8px 12px;
  background: rgba(193, 151, 69, 0.05);
  border: 1px solid rgba(193, 151, 69, 0.15);
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #C19745;

  .count {
    font-size: 18px;
    font-weight: 300;
    color: #F5F6F7;
  }

  .label {
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }
}
```

---

## 8. Module Components

### 8.1 Module Panel

Each of Planning, Execution, Evaluation, Coordination gets:

```css
.module {
  background: #2A2D33;
  border: 1px solid rgba(193, 151, 69, 0.1);
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 16px;
}

.module-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: rgba(193, 151, 69, 0.05);
  border-bottom: 1px solid rgba(193, 151, 69, 0.15);
}

.module-icon {
  width: 20px;
  height: 20px;
  color: #C19745;
}

.module-title {
  font-size: 13px;
  font-weight: 600;
  color: #C19745;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.module-id {
  margin-left: auto;
  font-size: 10px;
  color: #8A8F99;
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.3px;
}

.module-content {
  padding: 16px;
  color: #F5F6F7;
}
```

---

## 9. Code & Log Display

### 9.1 Code Blocks

```css
.code-block {
  background: #1B1E24;
  border: 1px solid rgba(193, 151, 69, 0.1);
  border-radius: 4px;
  padding: 12px;
  overflow-x: auto;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  line-height: 1.6;
  color: #F5F6F7;
  margin: 12px 0;

  .keyword {
    color: #7B5FF1;
  }

  .string {
    color: #49C883;
  }

  .number {
    color: #E8A64D;
  }

  .comment {
    color: #8A8F99;
  }

  .error {
    color: #EF4444;
  }
}
```

### 9.2 Logs/Terminal

```css
.log-container {
  background: #1B1E24;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 4px;
  padding: 12px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  line-height: 1.6;
  max-height: 400px;
  overflow-y: auto;
  color: #F5F6F7;
}

.log-entry {
  display: flex;
  gap: 8px;
  margin-bottom: 4px;

  .timestamp {
    color: #8A8F99;
    min-width: 80px;
  }

  .level {
    min-width: 60px;
    font-weight: 600;
  }

  .level.info {
    color: #6A87A6;
  }

  .level.success {
    color: #49C883;
  }

  .level.warning {
    color: #E8A64D;
  }

  .level.error {
    color: #EF4444;
  }

  .message {
    flex: 1;
    color: #F5F6F7;
  }
}
```

---

## 10. Dark Mode (Default & Only Mode)

VibeForge_BDS is **dark-mode-only**. No light mode toggle.

```css
/* Root */
:root {
  /* Colors */
  --color-bg-primary: #1B1E24;
  --color-bg-secondary: #2A2D33;
  --color-border: rgba(255, 255, 255, 0.08);
  --color-border-accent: rgba(193, 151, 69, 0.15);
  --color-text-primary: #F5F6F7;
  --color-text-secondary: #8A8F99;
  --color-text-tertiary: rgba(138, 143, 153, 0.6);
  --color-accent-primary: #C19745;
  --color-accent-secondary: #7B5FF1;
  --color-success: #49C883;
  --color-warning: #E8A64D;
  --color-error: #EF4444;

  /* Typography */
  --font-heading: 'Cinzel', serif;
  --font-body: 'Inter', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;

  /* Spacing */
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 12px;
  --spacing-lg: 16px;
  --spacing-xl: 24px;

  /* Shadows (subtle) */
  --shadow-sm: 0 2px 4px rgba(0, 0, 0, 0.2);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.25);
  --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.3);
}

body {
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  font-family: var(--font-body);
}
```

---

## 11. Visual Differences: Public vs BDS

| Aspect | Public VibeForge | VibeForge_BDS |
|--------|------------------|---------------|
| **Background** | Gradient (playful) | Solid Midnight Slate |
| **Border Radius** | 8-12px | 4-6px (sharp) |
| **Spacing** | 16-20px | 12px (tight) |
| **Colors** | Bright neon-adjacent | Muted, professional |
| **Typography** | Inter all the way | Cinzel + Inter + Mono |
| **Sidebar** | Optional overlay | Fixed, always visible |
| **Mode** | Light + Dark toggle | Dark only |
| **Feel** | Creative tool | Enterprise system |
| **Icons** | Rounded, playful | Thin-line, technical |
| **Shadows** | Soft, subtle | Minimal |

---

## 12. Implementation Checklist

### Phase 1: Color System

- [ ] Add BDS colors to Tailwind config
- [ ] Create CSS custom properties (variables)
- [ ] Update all component classes
- [ ] Remove public VibeForge gradient backgrounds

### Phase 2: Typography

- [ ] Install Cinzel + JetBrains Mono fonts
- [ ] Set up font imports
- [ ] Apply type scale to components
- [ ] Update code block styling

### Phase 3: Layout & Sidebar

- [ ] Create fixed sidebar (260px)
- [ ] Update main content margin-left
- [ ] Build sidebar navigation
- [ ] Add header (56px height)

### Phase 4: Components

- [ ] Restyle buttons (rounded corners → 4px)
- [ ] Update input fields
- [ ] Restyle cards/panels
- [ ] Create module components
- [ ] Update table styling

### Phase 5: Identity & Branding

- [ ] Add BDS Edition badge
- [ ] Add internal watermark
- [ ] Create skill count badge
- [ ] Add SAS indicator
- [ ] Implement module IDs

### Phase 6: Code & Logs

- [ ] Create code block component
- [ ] Create log display component
- [ ] Add syntax highlighting
- [ ] Add log levels (info, warn, error)

### Phase 7: Testing & Polish

- [ ] Cross-browser testing
- [ ] Responsive design check
- [ ] Color contrast validation (WCAG AA)
- [ ] Performance optimization

---

## 13. Brand Assets Files

You'll need these font files:

```
public/fonts/
├── Cinzel-Light.woff2
├── Inter-Regular.woff2
├── Inter-Medium.woff2
├── Inter-SemiBold.woff2
├── JetBrainsMono-Regular.woff2
└── JetBrainsMono-Bold.woff2
```

---

## 14. Quick Reference: CSS Variables

Copy this into your base CSS:

```css
:root {
  /* Palette */
  --midnight: #1B1E24;
  --brass: #C19745;
  --steel-blue: #6A87A6;
  --graphite: #2A2D33;
  --cool-gray: #8A8F99;
  --violet: #7B5FF1;
  --success: #49C883;
  --warning: #E8A64D;
  --error: #EF4444;
  --white: #FFFFFF;
  --off-white: #F5F6F7;

  /* Typography */
  --heading: 'Cinzel', serif;
  --body: 'Inter', sans-serif;
  --mono: 'JetBrains Mono', monospace;

  /* Spacing */
  --gap-xs: 4px;
  --gap-sm: 8px;
  --gap-md: 12px;
  --gap-lg: 16px;
  --gap-xl: 24px;
  --gap-2xl: 32px;

  /* Shadows */
  --shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.3);

  /* Borders */
  --border: 1px solid rgba(255, 255, 255, 0.08);
  --border-brass: 1px solid rgba(193, 151, 69, 0.15);
}
```

---

## 15. Summary

**VibeForge_BDS is VibeForge for serious work.**

✓ Same powerful features  
✓ Elevated visual presentation  
✓ Professional color palette  
✓ Tighter, smarter spacing  
✓ Premium typography  
✓ Enterprise-grade components  
✓ Clear internal identity  
✓ Dark mode only (no toggle friction)  

**Result:** A tool that commands respect, reduces cognitive load, and feels like enterprise infrastructure.

---

**Version:** 1.0 (Complete)  
**Status:** Ready for Implementation  
**Estimated Build Time:** 2-3 weeks (parallel with ForgeCommand integration)  

---

## 🎯 Next Steps

1. **Get fonts:** Download Cinzel & JetBrains Mono
2. **Create Tailwind config:** Implement color palette
3. **Build sidebar:** Fixed navigation structure
4. **Component update:** Restyle all UI elements
5. **Test & iterate:** Validate design system
6. **Ship to production:** Celebrate 🎉

---

**Built by:** Boswell Digital Solutions LLC  
**For:** Internal Engineering  
**Date:** December 8, 2025
