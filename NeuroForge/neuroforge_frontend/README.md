# NeuroForge Frontend

Professional control cockpit for the NeuroForge cognitive inference engine. Built with **SvelteKit 5**, **Tailwind CSS v4**, **TypeScript**, and designed for desktop (web + Tauri) deployment.

## Project Status

**Status**: ✅ Project scaffolding complete (November 19, 2025)

- ✅ SvelteKit project structure created
- ✅ Tailwind CSS v4 configured with Forge design tokens
- ✅ TypeScript types for all domain models
- ✅ Centralized API client (axios-based)
- ✅ Global stores (Svelte 5 runes)
- ✅ Main layout with navigation and app bar
- ✅ Overview dashboard page (skeleton)
- ✅ Page structure for all major sections

**Next Phase**: Implement individual pages (Pipelines, Domains, Models, Evaluations, Logs, Playground, Settings, Analytics)

## Tech Stack

- **Framework**: SvelteKit 2.x + Svelte 5 (latest)
- **Language**: TypeScript 5.9
- **Styling**: Tailwind CSS v4 with custom Forge design tokens
- **HTTP**: Axios with request/response interceptors
- **State**: Svelte stores with persistence layer
- **Build**: Vite 7.x
- **Icons**: Lucide-svelte

## Getting Started

### Prerequisites

- Node.js 18+
- npm 9+

### Installation

```bash
cd neuroforge_frontend
npm install
```

### Development

```bash
npm run dev
```

Opens on `http://localhost:5173` with hot reload enabled.

### Production Build

```bash
npm run build
npm run preview
```

## Project Structure

```
neuroforge_frontend/
├── src/
│   ├── app.css                       # Global CSS with Forge tokens
│   ├── routes/
│   │   ├── +layout.svelte            # Main layout (nav + header)
│   │   ├── overview/+page.svelte     # Dashboard
│   │   ├── pipelines/+page.svelte    # Pipeline management
│   │   ├── domains/+page.svelte      # Domain configuration
│   │   ├── models/+page.svelte       # Model catalog & routing
│   │   ├── evaluations/+page.svelte  # Evaluation runs
│   │   ├── logs/+page.svelte         # Audit trail & logs
│   │   ├── playground/+page.svelte   # Prompt testing
│   │   ├── analytics/+page.svelte    # Phase 3.0 analytics
│   │   └── settings/+page.svelte     # App configuration
│   └── lib/
│       ├── api/
│       │   └── neuroforge.ts         # Axios client + endpoints
│       ├── stores/
│       │   └── index.ts              # Global Svelte stores
│       ├── components/
│       │   ├── layout/               # Layout components
│       │   └── ui/                   # Reusable UI components
│       └── types/
│           └── index.ts              # TypeScript domain models
├── static/                           # Static assets
├── tailwind.config.ts                # Tailwind configuration
├── vite.config.ts                    # Vite configuration
├── tsconfig.json                     # TypeScript configuration
└── package.json
```

## Design System

### Color Tokens (Forge Palette)

All colors use Forge design tokens with dark-mode-first approach:

- **forge-ash**: Background & surfaces (50-900 scale)
- **forge-ember**: Primary accent & CTAs (50-900 scale, especially 600)
- **forge-brass**: Highlights & borders (50-900 scale, especially 400/500)
- **forge-ink**: Text & typography (50-900 scale)

### Example Usage

```svelte
<!-- Light text on ember background -->
<button class="bg-forge-ember-600 text-white hover:bg-forge-ember-700 dark:bg-forge-ember-700">
  Click me
</button>

<!-- Card with brass border -->
<div class="bg-forge-ash-100 dark:bg-forge-ash-800 border border-forge-brass-300 dark:border-forge-brass-700 rounded-lg">
  Card content
</div>
```

## API Integration

### Centralized Client

All API calls use the singleton client in `src/lib/api/neuroforge.ts`:

```typescript
import { neuroforgeApi } from '$lib/api/neuroforge';

// Fetch pipelines
const response = await neuroforgeApi.fetchPipelines();
if (response.success) {
  const pipelines = response.data;
}

// Run inference
const result = await neuroforgeApi.runInference({
  domain: 'literary',
  taskType: 'analysis',
  contextPackId: 'pack_123',
  userQuery: 'Analyze themes'
});
```

### Features

- Request/response interceptors for error handling
- Automatic correlation ID generation (X-Request-ID header)
- 30s default timeout
- Structured `ApiResponse<T>` wrapper for all endpoints
- Full type coverage with TypeScript

### Environment Configuration

Create `.env.local` in project root:

```env
VITE_BACKEND_URL=http://localhost:8000/api/v1
VITE_ENVIRONMENT=development
```

## Global Stores

Located in `src/lib/stores/index.ts`:

### Theme Store

```typescript
import { theme, toggleTheme } from '$lib/stores';

// Subscribe to theme changes
$: isDark = $theme === 'dark';

// Toggle theme
toggleTheme();
```

### App State Store

```typescript
import { appState, setLoading, setError, showNotification } from '$lib/stores';

setLoading(true);
setError('Operation failed');
showNotification('Success!', 'success');
```

### Navigation Store

```typescript
import { navState, navigateTo, selectDomain } from '$lib/stores';

navigateTo('pipelines');
selectDomain('literary');
```

### Playground State

```typescript
import { playgroundState, updatePlaygroundQuery, setPlaygroundResult } from '$lib/stores';

updatePlaygroundQuery('New query');
setPlaygroundResult(inferenceResult);
```

### Preferences Store (Persisted)

```typescript
import { preferences } from '$lib/stores';

// Load from localStorage on mount
onMount(() => preferences.load());

// Save preferences
preferences.save({ defaultDomain: 'market', compactMode: true });

// Reset to defaults
preferences.reset();
```

## TypeScript Types

Comprehensive types in `src/lib/types/index.ts`:

```typescript
import type {
  Domain, TaskType, ModelProvider,
  PipelineConfig, DomainConfig, ModelCatalog,
  InferenceRequest, InferenceResult,
  EvaluationRun, LogEntry
} from '$lib/types';

const pipeline: PipelineConfig = {
  id: 'pipe_1',
  name: 'Literary Analysis',
  domain: Domain.LITERARY,
  // ...
};
```

## Pages & Workflows

### Overview Dashboard
- High-level status snapshot
- Active domains, models, recent runs
- Error rate & cost metrics
- Quick links to key sections

### Pipelines
- List with filtering & sorting
- Detail view with pipeline graph
- Create/edit/delete pipelines
- Domain & adapter selection
- Model routing configuration

### Domains & Adapters
- Domain list (literary, market, general, custom)
- Prompt template editor
- Policy token management
- Context scope configuration
- Evaluation rubric customization

### Models & Routing
- Model catalog with health indicators
- Local (Ollama) vs remote (Claude, GPT) inventory
- Routing rules editor
- Champion model tracking
- Cost & latency metrics

### Evaluations & Experiments
- Evaluation run history
- Batch testing interface
- Score breakdown by dimension
- Model comparison & champion selection
- Trend analysis

### Logs & Provenance
- Queryable log viewer (date, level, service, domain filters)
- Full correlation ID tracing
- DataForge provenance link
- Export capabilities

### Playground
- Rich prompt + context input editor
- Domain & pipeline selector
- Model override option
- Inference execution with real-time status
- Output display with metadata & evaluation tags
- History of recent runs

### Analytics (Phase 3.0)
- Performance trends over time
- Comparative model analysis
- 6-24h performance predictions
- Anomaly detection with alerts
- Model health scoring
- Champion transition forecasts

### Settings
- Environment configuration (dev/staging/prod)
- Local vs remote model priority
- Token limits & timeouts
- Cost caps
- Feature flags & experimental toggles

## Component Architecture

### Layout Components
- `Navigation`: Left sidebar with page links
- `AppBar`: Top header with theme toggle & user menu
- `MainContainer`: Page content area

### UI Components (To Be Built)
- `Card`: Styled container
- `Button`: Primary/secondary variants
- `Table`: Sortable & filterable
- `Modal`: For confirmations & forms
- `Tooltip`: Info hints
- `Badge`: Status indicators
- `Skeleton`: Loading placeholders

### Patterns

**Data Fetching with Loading & Error States**:
```svelte
<script>
  let data = null;
  let loading = true;
  let error = null;

  onMount(async () => {
    try {
      const response = await neuroforgeApi.fetchSomething();
      if (response.success) {
        data = response.data;
      } else {
        error = response.error?.message;
      }
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });
</script>

{#if loading}
  <Skeleton />
{:else if error}
  <ErrorBox {error} />
{:else}
  <Content {data} />
{/if}
```

**Reactive State with Stores**:
```svelte
<script>
  import { playgroundState, updatePlaygroundQuery } from '$lib/stores';
</script>

<textarea bind:value={$playgroundState.query} on:input={(e) => updatePlaygroundQuery(e.target.value)} />
```

## Development Checklist

- [ ] Implement Pipelines page with CRUD
- [ ] Implement Domains editor with prompt templates
- [ ] Implement Models catalog with health dashboard
- [ ] Implement Evaluations runner & comparison UI
- [ ] Implement Logs viewer with filters
- [ ] Implement Playground with real-time execution
- [ ] Implement Analytics dashboards (Phase 3.0)
- [ ] Implement Settings panel
- [ ] Create reusable UI component library
- [ ] Add Tauri desktop wrapper (if needed)
- [ ] Implement error boundary components
- [ ] Add keyboard shortcuts
- [ ] Add dark/light mode persistence
- [ ] Performance optimization & code splitting
- [ ] E2E testing with Playwright
- [ ] Documentation & storybook

## Running with NeuroForge Backend

### Prerequisites

Backend must be running on `http://localhost:8000`:

```bash
cd ../neuroforge_backend
make dev
```

### Frontend Dev Server

```bash
npm run dev
```

Both will run concurrently. Frontend fetches from backend automatically.

## Tauri Desktop Build (Future)

To wrap as Tauri desktop app:

```bash
npm install @tauri-apps/cli @tauri-apps/api

# Generate Tauri config
npm run tauri init

# Dev mode
npm run tauri dev

# Build
npm run tauri build
```

## Deployment

### Vercel / Netlify

```bash
npm run build
```

Deploy the `build/` directory. No backend required in production (CORS proxy at API endpoint).

### Docker

```dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
COPY --from=build /app/build ./build
COPY package.json ./
RUN npm ci --only=production
CMD ["node", "-e", "import('./build/index.js')"]
```

## Contributing

- Follow existing code style (Svelte 5 runes, TypeScript)
- Use Tailwind classes + Forge tokens
- Write components small and focused
- Add types to all props and returns
- Persist preferences to localStorage when appropriate

## License

Licensed under Boswell Digital Solutions LLC terms. See parent project LICENSE.

## Support

For issues or questions, contact Charles Boswell or refer to NeuroForge backend documentation.
