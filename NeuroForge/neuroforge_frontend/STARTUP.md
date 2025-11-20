# NeuroForge Frontend - Startup Guide

**Project Created**: November 19, 2025  
**Status**: ✅ Scaffolding Complete & Build Verified

## Quick Start (60 seconds)

```bash
cd /home/charles/projects/Coding2025/Forge/neuroforge_frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Opens on **http://localhost:5173**

## What's Included

### ✅ Complete Foundation
- **SvelteKit 2** + **Svelte 5** (latest runes syntax)
- **Tailwind CSS v4** with Forge design tokens (ash/ember/brass/ink)
- **TypeScript 5.9** with full domain modeling
- **Axios HTTP client** with correlation IDs & error handling
- **Global Svelte stores** (theme, app state, nav, playground, preferences)
- **Professional layout** with nav rail, top bar, dark mode toggle
- **Overview dashboard** with real stats display
- **Production build** tested & verified (✔ 0 errors)

### Project Structure
```
src/
├── app.css                          # Global styles (Forge tokens)
├── routes/
│   ├── +layout.svelte              # Main layout (shared by all pages)
│   ├── overview/+page.svelte       # Dashboard with stats
│   ├── pipelines/
│   ├── domains/
│   ├── models/
│   ├── evaluations/
│   ├── logs/
│   ├── playground/
│   ├── settings/
│   └── analytics/
├── lib/
│   ├── api/neuroforge.ts           # NeuroForge API client (30+ endpoints)
│   ├── stores/index.ts             # Global state management
│   └── types/index.ts              # Complete TypeScript models
```

## Commands

```bash
# Development (hot reload)
npm run dev

# Type checking
npm run check

# Production build
npm run build

# Preview build locally
npm run preview
```

## Next Steps (Implementation Priority)

### Phase 1: Core Pages (Week 1-2)
1. **Pipelines** page (list, create, edit, delete)
2. **Models** catalog with health dashboard
3. **Playground** with inference execution

### Phase 2: Advanced Pages (Week 2-3)
4. **Evaluations** with comparison UI
5. **Logs** viewer with filtering
6. **Analytics** (Phase 3.0 dashboards)

### Phase 3: Polish (Week 3-4)
7. **Settings** configuration panel
8. UI component library (Card, Button, Table, Modal)
9. Error boundaries & loading states
10. Responsive design & accessibility

### Phase 4: Desktop (Optional)
11. Tauri wrapper for desktop app
12. Local file access for imports/exports
13. Native notifications & system integration

## Design System Reference

### Colors (Tailwind Classes)
```
Light Mode          Dark Mode
forge-ash-50        forge-ash-900
forge-ember-600     forge-ember-600 (primary)
forge-brass-400     forge-brass-700
forge-ink-900       forge-ink-50
```

### Usage Examples
```svelte
<!-- Primary button -->
<button class="bg-forge-ember-600 hover:bg-forge-ember-700 text-white">
  Click
</button>

<!-- Card -->
<div class="bg-forge-ash-100 dark:bg-forge-ash-800 rounded-lg p-4 
            border border-forge-brass-300 dark:border-forge-brass-700">
  Content
</div>
```

## Backend Integration

Ensure NeuroForge backend is running:

```bash
# Terminal 1: Start backend
cd ../neuroforge_backend
make dev

# Terminal 2: Start frontend
cd ../neuroforge_frontend
npm run dev
```

### Environment (.env.local)
```env
VITE_BACKEND_URL=http://localhost:8000/api/v1
VITE_ENVIRONMENT=development
```

### API Client Usage
```typescript
import { neuroforgeApi } from '$lib/api/neuroforge';

// All endpoints typed
const response = await neuroforgeApi.fetchPipelines();
if (response.success) {
  const pipelines = response.data;
}
```

## Type Coverage

All models strongly typed:
- `Domain`, `TaskType`, `ModelProvider`, `RoutingStrategy`
- `PipelineConfig`, `DomainConfig`, `ModelCatalog`
- `InferenceRequest`, `InferenceResult`, `EvaluationRun`
- `LogEntry`, `ProvenanceRecord`
- Full `ApiResponse<T>` wrapper for all endpoints

## Development Checklist

Before implementing each feature:
- [ ] Define types in `src/lib/types/index.ts`
- [ ] Add API methods to `src/lib/api/neuroforge.ts`
- [ ] Create page in `src/routes/<section>/+page.svelte`
- [ ] Use Forge color tokens consistently
- [ ] Handle loading/error/success states
- [ ] Add to navigation in `src/routes/+layout.svelte`
- [ ] Test with `npm run check` (TypeScript)
- [ ] Run `npm run build` before commit

## Build Verification

✅ Production build passes:
```
vite build → ✔ done
npm run build → Success (27 modules)
```

## Key Files to Understand

1. **`src/routes/+layout.svelte`** - Navigation & theme toggle
2. **`src/lib/api/neuroforge.ts`** - HTTP client with all endpoints
3. **`src/lib/stores/index.ts`** - Global state (theme, nav, playground)
4. **`src/lib/types/index.ts`** - Domain models & TypeScript interfaces
5. **`src/routes/overview/+page.svelte`** - Example page with API call

## Troubleshooting

**Port 5173 already in use?**
```bash
npm run dev -- --port 5174
```

**Tailwind classes not showing?**
```bash
rm -rf .svelte-kit node_modules/.vite
npm run build
```

**API call 404?**
- Verify backend running: `curl http://localhost:8000/api/v1/health`
- Check `VITE_BACKEND_URL` in `.env.local`

## Resources

- [SvelteKit Docs](https://kit.svelte.dev)
- [Svelte 5 Docs](https://svelte.dev)
- [Tailwind CSS v4](https://tailwindcss.com/blog/tailwindcss-v4)
- [NeuroForge Backend API](../neuroforge_backend/README.md)

## Architecture Decisions

- **SvelteKit** over Next.js: Lightweight, Svelte reactivity, built-in routing
- **Tailwind v4** over Styled Components: Utility-first, custom tokens, dark mode
- **Axios** over fetch: Interceptors, timeout handling, request cancellation
- **Svelte stores** over Context: Simpler, persists to localStorage
- **Monorepo layout**: Frontend & backend siblings, shared git history

---

**Ready to code?** Start with creating the Pipelines page or Playground!
