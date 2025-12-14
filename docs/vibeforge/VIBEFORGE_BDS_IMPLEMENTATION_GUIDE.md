# VibeForge_BDS Design System Implementation Guide

**Version:** 1.0  
**Target:** VibeForge_BDS Frontend  
**Estimated Time:** 2-3 weeks  
**Status:** Ready to Execute  

---

## Overview

This guide walks you through implementing the VibeForge_BDS design system across your SvelteKit application. The system transforms the public VibeForge UI into an enterprise-grade internal tool with subtle but powerful visual authority.

---

## Phase 1: Setup & Fonts (3 hours)

### 1.1 Download Fonts

You need three font families:

1. **Cinzel** (Light 300)
   - Download from: https://fonts.google.com/specimen/Cinzel
   - Files: `Cinzel-Light.woff2`

2. **Inter** (Regular 400, Medium 500, Semibold 600)
   - Download from: https://fonts.google.com/specimen/Inter
   - Files: `Inter-Regular.woff2`, `Inter-Medium.woff2`, `Inter-SemiBold.woff2`

3. **JetBrains Mono** (Regular 400, Bold 700)
   - Download from: https://fonts.jetbrains.com/
   - Files: `JetBrainsMono-Regular.woff2`, `JetBrainsMono-Bold.woff2`

### 1.2 Create Font Folder & Files

```bash
mkdir -p static/fonts
# Copy all .woff2 files into static/fonts/
```

### 1.3 Create Font CSS File

**File: `src/lib/styles/fonts.css`**

```css
/* Cinzel - Headings */
@font-face {
  font-family: 'Cinzel';
  src: url('/fonts/Cinzel-Light.woff2') format('woff2');
  font-weight: 300;
  font-style: normal;
  font-display: swap;
}

/* Inter - Body */
@font-face {
  font-family: 'Inter';
  src: url('/fonts/Inter-Regular.woff2') format('woff2');
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}

@font-face {
  font-family: 'Inter';
  src: url('/fonts/Inter-Medium.woff2') format('woff2');
  font-weight: 500;
  font-style: normal;
  font-display: swap;
}

@font-face {
  font-family: 'Inter';
  src: url('/fonts/Inter-SemiBold.woff2') format('woff2');
  font-weight: 600;
  font-style: normal;
  font-display: swap;
}

/* JetBrains Mono - Code */
@font-face {
  font-family: 'JetBrains Mono';
  src: url('/fonts/JetBrainsMono-Regular.woff2') format('woff2');
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}

@font-face {
  font-family: 'JetBrains Mono';
  src: url('/fonts/JetBrainsMono-Bold.woff2') format('woff2');
  font-weight: 700;
  font-style: normal;
  font-display: swap;
}
```

### 1.4 Update Main CSS

**File: `src/app.css`** - Add at the top:

```css
@import './lib/styles/fonts.css';

/* Root variables */
:root {
  /* Colors */
  --midnight: #1B1E24;
  --brass: #C19745;
  --steel-blue: #6A87A6;
  --graphite: #2A2D33;
  --cool-gray: #8A8F99;
  --bds-violet: #7B5FF1;
  --success: #49C883;
  --warning: #E8A64D;
  --error: #EF4444;
  --off-white: #F5F6F7;
  
  /* Typography */
  --font-heading: 'Cinzel', serif;
  --font-body: 'Inter', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}

body {
  background: var(--midnight);
  color: var(--off-white);
  font-family: var(--font-body);
}

html, body {
  margin: 0;
  padding: 0;
  height: 100%;
}
```

### 1.5 Replace Tailwind Config

Replace `tailwind.config.js` with the provided `tailwind.config.bds.js`:

```bash
cp tailwind.config.bds.js tailwind.config.js
```

### 1.6 Verify

```bash
npm run build
# No errors = success
```

---

## Phase 2: Layout Components (5 hours)

### 2.1 Create Sidebar Component

**File: `src/lib/components/Sidebar.svelte`**

```svelte
<script>
  import { page } from '$app/stores';
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher();

  const navItems = [
    { label: 'Dashboard', href: '/vibeforge-bds', icon: '📊' },
    { label: 'Skills Library', href: '/vibeforge-bds/skills', icon: '📚' },
    { label: 'Planning', href: '/vibeforge-bds/planning', icon: '🧠' },
    { label: 'Execution', href: '/vibeforge-bds/execution', icon: '⚙️' },
    { label: 'Evaluation', href: '/vibeforge-bds/evaluation', icon: '✓' },
    { label: 'Coordination', href: '/vibeforge-bds/coordination', icon: '🔗' },
    { label: 'System Logs', href: '/vibeforge-bds/logs', icon: '📋' },
    { label: 'BDS Settings', href: '/vibeforge-bds/settings', icon: '⚙️' },
  ];
</script>

<aside class="sidebar">
  <div class="sidebar-header">
    <div class="sidebar-logo">VibeForge_BDS</div>
    <div class="bds-identity">
      INTERNAL • BDS ENGINEERING
    </div>
  </div>

  <nav class="sidebar-nav">
    {#each navItems as item}
      <a
        href={item.href}
        class="sidebar-nav-item"
        class:active={$page.route.id?.includes(item.href.split('/').pop())}
      >
        <span class="icon">{item.icon}</span>
        <span class="label">{item.label}</span>
      </a>
    {/each}
  </nav>

  <div class="sidebar-footer">
    <div class="sidebar-status">
      <div>charles@bds.com</div>
      <div class="skill-badge">120 Skills</div>
      <div class="sas-indicator">
        <span class="status-dot"></span>
        SAS: ON
      </div>
    </div>
  </div>
</aside>

<style>
  .sidebar {
    width: 260px;
    background: var(--midnight);
    border-right: 1px solid rgba(193, 151, 69, 0.15);
    padding: 16px 0;
    position: fixed;
    left: 0;
    top: 0;
    height: 100vh;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
  }

  .sidebar-header {
    padding: 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    margin-bottom: 12px;
  }

  .sidebar-logo {
    font-family: var(--font-heading);
    font-size: 18px;
    font-weight: 300;
    color: var(--brass);
    letter-spacing: 0.5px;
    margin-bottom: 8px;
  }

  .bds-identity {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--graphite);
    color: var(--brass);
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    border: 1px solid rgba(193, 151, 69, 0.2);
  }

  .bds-identity::before {
    content: '';
    display: inline-block;
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: var(--brass);
  }

  .sidebar-nav {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 0 8px;
    flex: 1;
  }

  .sidebar-nav-item {
    padding: 10px 12px;
    color: var(--cool-gray);
    border-left: 2px solid transparent;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 13px;
    text-decoration: none;
  }

  .sidebar-nav-item:hover {
    color: var(--brass);
    background: rgba(193, 151, 69, 0.08);
    border-left-color: var(--brass);
  }

  .sidebar-nav-item.active {
    color: var(--brass);
    background: rgba(193, 151, 69, 0.1);
    border-left-color: var(--brass);
    font-weight: 500;
  }

  .icon {
    font-size: 16px;
  }

  .label {
    flex: 1;
  }

  .sidebar-footer {
    position: relative;
    padding: 16px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    text-align: center;
  }

  .sidebar-status {
    font-size: 11px;
    color: var(--cool-gray);
    line-height: 1.6;
  }

  .skill-badge {
    font-size: 10px;
    color: var(--brass);
    font-weight: 600;
    margin: 4px 0;
  }

  .sas-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    font-size: 10px;
    color: var(--success);
  }

  .status-dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--success);
  }
</style>
```

### 2.2 Create Header Component

**File: `src/lib/components/Header.svelte`**

```svelte
<script>
  export let title = 'Dashboard';
  let currentTime = new Date().toLocaleTimeString();

  setInterval(() => {
    currentTime = new Date().toLocaleTimeString();
  }, 1000);
</script>

<header class="header">
  <div class="header-left">
    <h1 class="header-title">{title}</h1>
  </div>

  <div class="header-right">
    <div class="header-user">charles@bds.com</div>
    <div class="header-badge">BDS Edition — v1.0.0</div>
    <div class="sas-indicator">
      <span class="status-dot"></span>
      SAS: ON
    </div>
    <div class="current-time">{currentTime}</div>
  </div>
</header>

<style>
  .header {
    height: 56px;
    background: var(--midnight);
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
    font-family: var(--font-heading);
    font-size: 16px;
    font-weight: 300;
    color: var(--brass);
    letter-spacing: 0.5px;
    margin: 0;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 20px;
  }

  .header-user {
    font-size: 12px;
    color: var(--cool-gray);
  }

  .header-badge {
    background: var(--graphite);
    border: 1px solid rgba(193, 151, 69, 0.2);
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 11px;
    color: var(--brass);
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.4px;
  }

  .sas-indicator {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--cool-gray);
  }

  .status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--success);
  }

  .current-time {
    font-size: 11px;
    color: var(--cool-gray);
    font-family: var(--font-mono);
    letter-spacing: 0.2px;
  }
</style>
```

### 2.3 Update Main Layout

**File: `src/routes/+layout.svelte`**

```svelte
<script>
  import Sidebar from '$lib/components/Sidebar.svelte';
  import Header from '$lib/components/Header.svelte';
  import '$lib/styles/app.css';
</script>

<div class="bds-app">
  <Sidebar />
  <Header title="Dashboard" />
  <main class="main-content">
    <slot />
  </main>
  <div class="watermark">
    Boswell Digital Solutions LLC • Internal Build
  </div>
</div>

<style>
  .bds-app {
    display: flex;
    height: 100vh;
    background: var(--midnight);
  }

  :global(body) {
    margin: 0;
    padding: 0;
    background: var(--midnight);
  }

  .main-content {
    flex: 1;
    margin-left: 260px;
    margin-top: 56px;
    overflow-y: auto;
    padding: 24px;
  }

  .watermark {
    position: fixed;
    bottom: 16px;
    right: 16px;
    font-size: 9px;
    color: rgba(193, 151, 69, 0.15);
    font-family: var(--font-body);
    text-align: right;
    pointer-events: none;
    z-index: 1;
  }
</style>
```

---

## Phase 3: Component Library (6 hours)

### 3.1 Create Button Component

**File: `src/lib/components/Button.svelte`**

```svelte
<script>
  export let variant = 'primary'; // 'primary' | 'secondary' | 'tertiary'
  export let size = 'md'; // 'sm' | 'md' | 'lg'
  export let disabled = false;
  export let type = 'button';
  export let href = null;

  const variantClasses = {
    primary: 'btn-primary',
    secondary: 'btn-secondary',
    tertiary: 'btn-tertiary',
  };

  const sizeClasses = {
    sm: 'text-xs px-3 py-1.5',
    md: 'text-sm px-4 py-2.5',
    lg: 'text-base px-6 py-3',
  };
</script>

{#if href}
  <a {href} class="btn {variantClasses[variant]} {sizeClasses[size]}" {disabled}>
    <slot />
  </a>
{:else}
  <button {type} {disabled} class="btn {variantClasses[variant]} {sizeClasses[size]}">
    <slot />
  </button>
{/if}

<style>
  .btn {
    border-radius: 4px;
    font-weight: 500;
    transition: all 0.15s;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    border: none;
    text-decoration: none;
    white-space: nowrap;
  }

  .btn-primary {
    background: var(--brass);
    color: var(--midnight);
  }

  .btn-primary:hover:not(:disabled) {
    background: #D4A859;
    box-shadow: 0 4px 12px rgba(193, 151, 69, 0.15);
  }

  .btn-secondary {
    background: transparent;
    color: var(--steel-blue);
    border: 1px solid var(--steel-blue);
  }

  .btn-secondary:hover:not(:disabled) {
    background: rgba(106, 135, 166, 0.1);
  }

  .btn-tertiary {
    background: transparent;
    color: var(--cool-gray);
  }

  .btn-tertiary:hover:not(:disabled) {
    color: var(--brass);
  }

  .btn:disabled {
    background: #555557;
    color: var(--cool-gray);
    cursor: not-allowed;
    opacity: 0.6;
  }
</style>
```

### 3.2 Create Input Component

**File: `src/lib/components/Input.svelte`**

```svelte
<script>
  export let label = '';
  export let type = 'text';
  export let placeholder = '';
  export let value = '';
  export let disabled = false;
  export let error = '';
  export let monospace = false;

  let inputElement;

  $: if (inputElement) inputElement.value = value;
</script>

<div class="input-group">
  {#if label}
    <label for="input">{label}</label>
  {/if}
  <input
    bind:this={inputElement}
    {type}
    {placeholder}
    {disabled}
    class:error
    class:monospace
    bind:value
    {...$$restProps}
  />
  {#if error}
    <div class="error-message">{error}</div>
  {/if}
</div>

<style>
  .input-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 12px;
  }

  label {
    font-size: 12px;
    font-weight: 500;
    color: var(--cool-gray);
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }

  input {
    padding: 10px 12px;
    background: var(--graphite);
    color: var(--off-white);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 4px;
    font-family: var(--font-body);
    font-size: 14px;
    transition: all 0.15s;
  }

  input.monospace {
    font-family: var(--font-mono);
    font-size: 12px;
  }

  input:focus {
    outline: none;
    border-color: var(--brass);
    box-shadow: 0 0 0 3px rgba(193, 151, 69, 0.1);
  }

  input:disabled {
    background: var(--midnight);
    color: #555557;
    cursor: not-allowed;
  }

  input::placeholder {
    color: var(--cool-gray);
  }

  input.error {
    border-color: var(--error);
  }

  .error-message {
    font-size: 11px;
    color: var(--error);
  }
</style>
```

### 3.3 Create Panel Component

**File: `src/lib/components/Panel.svelte`**

```svelte
<script>
  export let title = '';
  export let subtitle = '';
  export let icon = '';
</script>

<div class="panel">
  {#if title || icon}
    <div class="panel-header">
      {#if icon}
        <span class="icon">{icon}</span>
      {/if}
      <div>
        {#if title}
          <div class="title">{title}</div>
        {/if}
        {#if subtitle}
          <div class="subtitle">{subtitle}</div>
        {/if}
      </div>
    </div>
  {/if}
  <div class="panel-content">
    <slot />
  </div>
</div>

<style>
  .panel {
    background: var(--graphite);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    overflow: hidden;
    margin-bottom: 16px;
  }

  .panel-header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(193, 151, 69, 0.03);
  }

  .icon {
    font-size: 18px;
  }

  .title {
    font-size: 14px;
    font-weight: 500;
    color: var(--off-white);
  }

  .subtitle {
    font-size: 11px;
    color: var(--cool-gray);
    margin-top: 2px;
  }

  .panel-content {
    padding: 16px;
    color: var(--off-white);
    font-size: 14px;
  }
</style>
```

---

## Phase 4: Theme Colors Across Pages (4 hours)

Go through each existing page and update Tailwind classes:

**Pattern:**
```svelte
<!-- Before (Public VibeForge) -->
<div class="bg-gradient-to-br from-violet-900 to-violet-700">

<!-- After (VibeForge_BDS) -->
<div class="bg-graphite border border-border-light rounded-md">
```

### Common Replacements:

```
from-violet-900/40 → bg-brass-transparent
border-violet-500 → border-border-brass
text-violet-300 → text-brass
bg-slate-800/50 → bg-graphite
border-slate-700 → border-border-light
rounded-lg → rounded-md
px-6 py-4 → px-4 py-3
gap-6 → gap-4
```

---

## Phase 5: Testing & Refinement (3 hours)

### 5.1 Visual Checklist

- [ ] Sidebar displays correctly (260px width)
- [ ] Header sticky at top
- [ ] All text readable on dark background
- [ ] Buttons have proper hover states
- [ ] Inputs focus with brass border
- [ ] Panels have subtle borders
- [ ] No bright neon colors
- [ ] Code blocks use JetBrains Mono
- [ ] Headings use Cinzel

### 5.2 Performance Check

```bash
npm run build
# Check bundle size - fonts should be ~100KB total
```

### 5.3 Cross-browser Testing

- [ ] Chrome
- [ ] Firefox
- [ ] Safari
- [ ] Edge

---

## Phase 6: Finalization (2 hours)

### 6.1 Add Watermark & Badges

All done in layout.svelte (step 2.3)

### 6.2 Document Component Usage

Create `COMPONENT_USAGE.md`:

```markdown
# VibeForge_BDS Component Library

## Button
```svelte
<Button variant="primary">Click me</Button>
<Button variant="secondary">Secondary</Button>
<Button variant="tertiary">Tertiary</Button>
```

## Input
```svelte
<Input label="Name" placeholder="Your name" monospace={false} />
```

## Panel
```svelte
<Panel title="My Panel" icon="⚙️">
  Content goes here
</Panel>
```
```

### 6.3 Commit & Deploy

```bash
git add .
git commit -m "VibeForge_BDS design system implementation complete"
git push
```

---

## Quick Tailwind Reference

```svelte
<!-- Colors -->
<div class="bg-midnight text-off-white">Dark background</div>
<div class="bg-graphite">Mid-tone panel</div>
<div class="text-brass">Accent text</div>

<!-- Typography -->
<h1 class="heading-1">Main Heading</h1>
<p class="text-body">Body text</p>
<code class="code-inline">code()</code>

<!-- Spacing -->
<div class="p-md m-lg gap-sm">Properly spaced</div>

<!-- Buttons -->
<button class="btn btn-primary">Primary</button>
<button class="btn btn-secondary">Secondary</button>

<!-- Panels & Cards -->
<div class="panel">
  <div class="panel-header">Header</div>
  <div class="panel-content">Content</div>
</div>

<!-- Tables -->
<table class="table">
  <thead class="table-head">
    <tr>
      <th class="table-header">Column</th>
    </tr>
  </thead>
  <tbody>
    <tr class="table-body-row">
      <td class="table-cell">Data</td>
    </tr>
  </tbody>
</table>

<!-- Badges -->
<span class="badge badge-success">Success</span>
<span class="badge badge-warning">Warning</span>
<span class="badge badge-error">Error</span>
```

---

## Troubleshooting

**Fonts not loading?**
- Check `static/fonts/` exists
- Check CSS imports in `src/app.css`
- Clear browser cache (Ctrl+Shift+Del)

**Colors look wrong?**
- Check Tailwind config is copied correctly
- Verify CSS variables in `:root`
- Clear Tailwind cache: `npm run build -- --reset`

**Spacing too loose?**
- Replace `gap-lg` with `gap-md`
- Replace `p-lg` with `p-md`
- Default is tighter than public VibeForge

---

## Summary

✅ Phase 1: Setup fonts & Tailwind config (3h)  
✅ Phase 2: Build layout components (5h)  
✅ Phase 3: Create component library (6h)  
✅ Phase 4: Update theme across pages (4h)  
✅ Phase 5: Test & validate (3h)  
✅ Phase 6: Finalize & deploy (2h)  

**Total: ~23 hours → 3 weeks (with breaks)**

Result: Enterprise-grade internal tool that commands respect without sacrificing usability.

---

**Ready to build?** Start with Phase 1 and proceed sequentially. 🚀
