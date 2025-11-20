# NeuroForge Frontend - Deep Dive

**Extends**: `../../.github/copilot-instructions.md` (dual-stack overview)  
**Scope**: Frontend-specific patterns, state management, component architecture

---

## Project Structure

**Three-layer architecture**:
1. **Routes** (`src/routes/`): SvelteKit pages with `+page.svelte` files (auto-routed)
2. **Business Logic** (`src/lib/`): Reusable API client, stores, types, components
3. **Design System** (`src/app.css`, `tailwind.config.ts`): Forge design tokens

---

## Tech Stack & Key Files

| File | Purpose | LOC |
|------|---------|-----|
| `src/lib/api/neuroforge.ts` | Axios HTTP client singleton | 600+ |
| `src/lib/stores/index.ts` | Svelte global state | 237 |
| `src/lib/types/index.ts` | TypeScript domain models | 267 |
| `tailwind.config.ts` | Forge color tokens | - |
| `vite.config.ts` | Build configuration | - |
| `src/routes/+layout.svelte` | App layout (nav, header, theme) | - |

**Tech**: SvelteKit 2.x, Svelte 5 (runes), TypeScript 5.9, Tailwind v4, Axios, Vite 7

---

## API Integration Pattern (CRITICAL)

### Using the API Client

```typescript
import { neuroforgeApi } from '$lib/api/neuroforge';

// All methods return ApiResponse<T>
const response = await neuroforgeApi.submitInference(request);

if (response.success) {
    console.log(response.data);      // Typed data (InferenceResult, etc.)
} else {
    console.error(response.error);   // Error message
}
```

**Key Rules**:
1. **Always use centralized client**: Import `neuroforgeApi` singleton
2. **Always check `response.success`** before accessing `response.data`
3. **Headers automatic**: Correlation IDs, Content-Type, X-Request-ID
4. **Timeout**: 30 seconds (configured in `src/lib/api/neuroforge.ts`)

### Backend URL Configuration

```typescript
// Loaded from environment variable
const backendUrl = import.meta.env.VITE_BACKEND_URL;
// or from store
const { backendUrl } = $appState;
```

**Environment** (`.env.local`, git-ignored):
```env
VITE_BACKEND_URL=http://localhost:8000/api/v1
VITE_ENVIRONMENT=development
```

---

## State Management (Svelte Stores)

### Import & Subscribe

```typescript
import { appState, setLoading, showNotification } from '$lib/stores';

// Auto-subscribe with $ prefix in components
let stats = $appState;  // Reactivity + auto-unsubscribe on destroy
```

### Available Stores

- **`theme`**: light/dark mode toggle with `toggleTheme()`
- **`appState`**: environment, loading state, errors, notifications
  - Setters: `setLoading(bool)`, `setError(error|null)`, `showNotification(msg, type)`
- **`navState`**: current page, sidebar, selected domain/pipeline
  - Setters: `navigateTo(page)`, `toggleSidebar()`, `selectDomain(domain)`
- **`playgroundState`**: prompt playground state (query, context, result)
- **`preferences`**: user preferences with `.load()` and `.save()` methods

### Store Architecture

```typescript
// In src/lib/stores/index.ts
export const appState = writable<AppState>({ ... });

// Derived stores for computed values
export const isLoading = derived(appState, $state => $state.loading);

// Updater functions (not direct store updates)
export function setLoading(value: boolean) {
    appState.update(state => ({ ...state, loading: value }));
}
```

**Pattern**: Define store as `writable`, export typed updater functions, subscribe with `$` prefix in components.

---

## TypeScript Types (Centralized)

All types in `src/lib/types/index.ts`:

```typescript
// Enums
export enum Domain { literary = 'literary', market = 'market', general = 'general' }
export enum TaskType { analysis, generation, reasoning, classification, extraction }
export enum ModelProvider { ollama, anthropic, openai }

// Request models
export interface InferenceRequest {
    domain: Domain;
    task_type: TaskType;
    context_pack_id: string;
    user_query: string;
    additional_context?: string;
    max_tokens?: number;
}

// Response models
export interface InferenceResult {
    inference_id: string;
    status: InferenceStatus;
    output: string;
    evaluation_score: number;
    model_id: string;
    latency_ms: number;
    correlation_id: string;
}

// Config models
export interface DomainConfig { ... }
export interface PipelineConfig { ... }
```

**Rule**: Never use `any`. Import and use strictly-typed interfaces from `types/index.ts`.

---

## Component Architecture

### Layout Components

- **`src/routes/+layout.svelte`**: App-wide layout
  - Navigation rail (left sidebar)
  - Top header bar with logo, search, theme toggle
  - Main content area
  - Footer

### Page Routes (Auto-Routed by SvelteKit)

```
src/routes/
├── +page.svelte              # /
├── +layout.svelte            # App layout
├── overview/
│   └── +page.svelte          # /overview (dashboard)
├── pipelines/
│   ├── +page.svelte          # /pipelines
│   └── [id]/+page.svelte     # /pipelines/:id
├── domains/+page.svelte      # /domains
├── models/+page.svelte       # /models
├── evaluations/+page.svelte  # /evaluations
├── logs/+page.svelte         # /logs
├── playground/+page.svelte   # /playground (prompt tester)
├── settings/+page.svelte     # /settings
└── analytics/+page.svelte    # /analytics (admin)
```

**Each page**:
1. Imports API client and stores
2. Calls `setLoading(true)` before API call
3. On success: Updates store, `setError(null)`, displays result
4. On error: Calls `showNotification(error)`, `setError(error)`

---

## Design System (Tailwind + Forge Tokens)

### Color Tokens

**Forge Design Tokens** (defined in `tailwind.config.ts`):

- **forge-ash**: Background/surfaces (neutral gray)
  - `bg-forge-ash-50` (lightest) → `bg-forge-ash-900` (darkest)
- **forge-ember**: Primary/CTAs (warm orange-red)
  - `bg-forge-ember-600` (primary), `hover:bg-forge-ember-700`
- **forge-brass**: Highlights/accents (gold)
  - `border-forge-brass-400`, `text-forge-brass-600`
- **forge-ink**: Text (dark neutral)
  - `text-forge-ink-900` (dark mode: white)

### Dark Mode Support

CSS automatically applies dark mode via `dark:` class variants. No manual theme switching in components.

```svelte
<button class="bg-forge-ember-600 hover:bg-forge-ember-700 dark:bg-forge-ember-700">
    Action
</button>
```

**Dark mode is toggled via `toggleTheme()`** in store. Automatically adds/removes `dark` class to `document.documentElement`.

### Component Example

```svelte
<script>
    import { appState, setLoading, showNotification } from '$lib/stores';
    import { neuroforgeApi } from '$lib/api/neuroforge';
    import type { InferenceRequest } from '$lib/types';
    
    let domain = 'literary';
    let taskType = 'analysis';
    let loading = false;
    
    async function handleSubmit() {
        setLoading(true);
        const response = await neuroforgeApi.submitInference({
            domain,
            task_type: taskType,
            context_pack_id: 'pack_123',
            user_query: 'Your query here',
        });
        setLoading(false);
        
        if (response.success) {
            showNotification('Inference submitted', 'success');
        } else {
            showNotification(response.error || 'Failed', 'error');
        }
    }
</script>

<button 
    class="bg-forge-ember-600 hover:bg-forge-ember-700 disabled:opacity-50"
    disabled={loading}
    on:click={handleSubmit}
>
    {loading ? 'Processing...' : 'Submit Inference'}
</button>
```

---

## Development Workflow

### Commands

```bash
npm run dev              # Dev server (localhost:5173) with hot reload
npm run build            # Production build (vite build)
npm run preview          # Test production build locally
npm run check            # TypeScript + svelte-check (strict mode)
npm run check:watch      # Watch mode for type checking
```

### Type Safety (Strict Mode)

- TypeScript strict mode enabled in `tsconfig.json`
- `svelte-check` enabled for component type checking
- **No implicit `any`** — always define types or let TypeScript infer
- Run `npm run check` before committing

### Create New Page

1. Create `src/routes/my-feature/+page.svelte`
2. SvelteKit auto-routes to `/my-feature`
3. Import layout components from shared layout
4. Import API client and stores as needed
5. Use type-safe requests/responses

### Add API Endpoint

1. Extend `NeuroForgeClient` class in `src/lib/api/neuroforge.ts`
2. Add typed method:
   ```typescript
   async submitInference(request: InferenceRequest): Promise<ApiResponse<InferenceResult>> {
       return this.request<InferenceResult>('POST', '/inference', request);
   }
   ```
3. Export from singleton

### Add Global State

1. Define store in `src/lib/stores/index.ts`
2. Export getter/updater functions
3. Subscribe in components with `$store` syntax

### Add Type Definition

1. Define in `src/lib/types/index.ts`
2. Import where needed
3. Keep all types centralized (no scattering)

---

## Component Reuse

### Shared UI Components

Location: `src/lib/components/ui/`
- Button, Card, Modal, Dropdown, Tabs, etc.
- Styled with Forge tokens
- Highly reusable, minimal props

### Layout Components

Location: `src/lib/components/layout/`
- Header, Sidebar, Footer
- Navigation logic
- Theme toggle integration

### Feature Components

Location: `src/lib/components/features/`
- Domain-specific (playground, analytics, etc.)
- Call API client
- Update stores
- Orchestrate multiple UI components

---

## API Response Handling Pattern

```typescript
// Standard pattern for all endpoints
async function fetchData() {
    setLoading(true);
    try {
        const response = await neuroforgeApi.getInferenceHistory();
        
        if (response.success) {
            // Use response.data (strongly typed)
            return response.data;
        } else {
            // Handle error
            showNotification(response.error || 'Failed to fetch', 'error');
            return null;
        }
    } catch (error) {
        // Network or other errors
        showNotification('Network error', 'error');
        return null;
    } finally {
        setLoading(false);
    }
}
```

**Key Points**:
1. Wrap in try/catch for network errors
2. Check `response.success` before using `.data`
3. Always call `setLoading()` before and after
4. Show errors via `showNotification()`
5. Use typed responses from types/index.ts

---

## Environment Variables

Create `.env.local` (git-ignored):

```env
VITE_BACKEND_URL=http://localhost:8000/api/v1
VITE_ENVIRONMENT=development
```

Access in code:
```typescript
const backendUrl = import.meta.env.VITE_BACKEND_URL;
const environment = import.meta.env.VITE_ENVIRONMENT;
```

---

## Folder Structure & Naming

```
src/
├── app.css                           # Global styles + Forge token definitions
├── routes/
│   ├── +layout.svelte               # App layout
│   ├── +page.svelte                 # Home page
│   └── [feature]/+page.svelte       # Feature pages
├── lib/
│   ├── api/
│   │   └── neuroforge.ts            # Axios singleton client (30+ endpoints)
│   ├── stores/
│   │   └── index.ts                 # Svelte stores (theme, appState, etc.)
│   ├── types/
│   │   └── index.ts                 # All TypeScript interfaces
│   ├── components/
│   │   ├── ui/                      # Shared UI components
│   │   ├── layout/                  # Layout components
│   │   └── features/                # Feature-specific components
│   └── utils/                       # Utility functions
└── static/
    └── vibe_A.png                   # Static assets
```

---

## Common Patterns & Best Practices

### Error Handling

```typescript
if (!response.success) {
    showNotification(response.error || 'An error occurred', 'error');
    setError(response.error);
    return;
}
```

### Loading States

```typescript
setLoading(true);
try {
    // Do work
} finally {
    setLoading(false);  // Always clear loading state
}
```

### Store Subscriptions

```svelte
<script>
    import { appState } from '$lib/stores';
    
    // Auto-subscribe + auto-unsubscribe on destroy
    let { loading, errors } = $appState;
</script>
```

### Type-Safe Form Submission

```svelte
<script>
    import type { InferenceRequest } from '$lib/types';
    import { Domain, TaskType } from '$lib/types';
    
    let request: InferenceRequest = {
        domain: Domain.literary,
        task_type: TaskType.analysis,
        context_pack_id: '',
        user_query: '',
    };
</script>

<form on:submit|preventDefault={handleSubmit}>
    <input bind:value={request.user_query} />
    <button type="submit">Submit</button>
</form>
```

---

## Performance & Optimization

- **Lazy load pages**: SvelteKit handles automatically via route-based code splitting
- **Store subscriptions**: Use `$store` syntax for auto-unsubscribe on destroy
- **Component imports**: Import only what's needed (tree-shaking enabled)
- **Tailwind JIT**: Styles compiled on-demand (no bloat)

---

## Production Build

```bash
npm run build   # Creates .svelte-kit/build/
npm run preview # Tests production build locally
```

**Checklist**:
- ✅ Environment variables set (`.env.local` or CI/CD)
- ✅ TypeScript check passes (`npm run check`)
- ✅ No console errors/warnings
- ✅ All routes working
- ✅ API calls to correct backend URL

---

## File Organization Principles

- **Centralized types**: All interfaces in `src/lib/types/index.ts`
- **Singleton API client**: Import `neuroforgeApi` from `$lib/api/neuroforge`, never create new instances
- **Store updaters**: Export functions, not direct store manipulation
- **Component reuse**: Share UI in `lib/components/ui/`, features in `lib/components/features/`
- **No hardcoded URLs**: Always use `import.meta.env.VITE_BACKEND_URL` or store
- **Responsive design**: Use Tailwind breakpoints and Forge tokens
- **Dark mode**: Use `dark:` class variants, not manual theme logic

---

## References

- SvelteKit docs: https://kit.svelte.dev/
- Svelte 5 runes: https://svelte.dev/docs/svelte-5-runes
- Tailwind CSS: https://tailwindcss.com/
- Axios: https://axios-http.com/
- TypeScript: https://www.typescriptlang.org/

