# FORGE COMMAND - TAURI APP SETUP GUIDE

**Complete guide to create the Forge Command Tauri desktop app from scratch**

---

## 🎯 WHAT WE'RE BUILDING

A Tauri desktop app with:
- ✅ Rust backend (IPC commands, database queries)
- ✅ SvelteKit frontend (dashboards, charts)
- ✅ TailwindCSS with Forge colors (blue, violet, cyan)
- ✅ System tray integration
- ✅ Native notifications
- ✅ PostgreSQL connection to DataForge database

---

## 📋 PREREQUISITES

```bash
# Install Rust (if not already installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Install Tauri CLI
cargo install tauri-cli

# Install Node.js 20+ (if not already installed)
# Use nvm or download from nodejs.org

# Verify installations
rustc --version
cargo --version
node --version
npm --version
```

---

## 🚀 STEP 1: CREATE PROJECT STRUCTURE

```bash
# Navigate to your Forge ecosystem directory
cd ~/projects/Coding2025/Forge

# Create ForgeCommand directory
mkdir ForgeCommand
cd ForgeCommand

# Initialize npm project
npm init -y

# Create SvelteKit project
npm create svelte@latest .
# Choose: Skeleton project, TypeScript, ESLint, Prettier

# Install SvelteKit dependencies
npm install

# Install Tauri
npm install -D @tauri-apps/cli @tauri-apps/api

# Initialize Tauri
npm run tauri init
```

**When prompted by `tauri init`:**
- App name: `forge-command`
- Window title: `Forge Command`
- Web assets: `../build` (SvelteKit default)
- Dev server: `http://localhost:5173`
- Dev command: `npm run dev`
- Build command: `npm run build`

---

## 🎨 STEP 2: INSTALL FRONTEND DEPENDENCIES

```bash
# TailwindCSS
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Chart.js for dashboards
npm install chart.js svelte-chartjs

# Date utilities
npm install date-fns

# Icons
npm install lucide-svelte
```

---

## 🎨 STEP 3: CONFIGURE TAILWIND WITH FORGE COLORS

Create `tailwind.config.js`:

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        // Forge brand colors
        'forge-black': '#0D0D0F',
        'forge-slate': '#1A1B1F',
        'forge-steel': '#2C2E33',
        'forge-ember': '#D97706',
        
        // Service colors
        'dataforge-blue': '#00A3FF',
        'neuroforge-violet': '#A855F7',
        'rake-cyan': '#2DD4BF',
        'rake-bronze': '#CD7F32',
        
        // Status colors
        'success': '#10B981',
        'error': '#EF4444',
        'warning': '#F59E0B'
      },
      fontFamily: {
        'sans': ['Inter', 'system-ui', 'sans-serif'],
        'display': ['Cinzel', 'serif'],
        'mono': ['JetBrains Mono', 'monospace']
      }
    }
  },
  plugins: []
}
```

---

## 🎨 STEP 4: CREATE APP CSS

Create `src/app.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Import fonts */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono&display=swap');

/* Global styles */
body {
  @apply bg-forge-black text-white font-sans;
  margin: 0;
  padding: 0;
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  @apply bg-forge-slate;
}

::-webkit-scrollbar-thumb {
  @apply bg-forge-steel rounded;
}

::-webkit-scrollbar-thumb:hover {
  @apply bg-forge-ember;
}

/* Custom component styles */
.panel {
  @apply bg-forge-slate rounded-lg border border-forge-steel;
}

.kpi-card {
  @apply panel p-6;
}

.status-badge {
  @apply px-3 py-1 rounded-full text-sm font-medium;
}

.status-badge.up {
  @apply bg-success/20 text-success;
}

.status-badge.degraded {
  @apply bg-warning/20 text-warning;
}

.status-badge.down {
  @apply bg-error/20 text-error;
}

/* Service-specific classes */
.dataforge {
  @apply text-dataforge-blue;
}

.neuroforge {
  @apply text-neuroforge-violet;
}

.rake {
  @apply text-rake-cyan;
}
```

---

## 🎨 STEP 5: SETUP SVELTE LAYOUT

Create `src/routes/+layout.svelte`:

```svelte
<script lang="ts">
  import '../app.css';
</script>

<div class="min-h-screen bg-forge-black text-white">
  <slot />
</div>
```

---

## 🦀 STEP 6: SETUP RUST BACKEND

Edit `src-tauri/Cargo.toml` and add dependencies:

```toml
[dependencies]
tauri = { version = "2", features = ["macos-private-api", "notification-all", "tray-icon"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
tokio = { version = "1", features = ["full"] }
sqlx = { version = "0.8", features = ["runtime-tokio-native-tls", "postgres", "uuid", "chrono"] }
uuid = { version = "1", features = ["v4"] }
chrono = "0.4"
```

---

## 🦀 STEP 7: CREATE RUST DATABASE MODULE

Create `src-tauri/src/database.rs`:

```rust
use sqlx::{postgres::PgPoolOptions, PgPool, Error};
use std::env;

pub async fn create_pool() -> Result<PgPool, Error> {
    let database_url = env::var("DATABASE_URL")
        .unwrap_or_else(|_| "postgresql://localhost:5432/dataforge".to_string());
    
    PgPoolOptions::new()
        .max_connections(5)
        .connect(&database_url)
        .await
}

#[derive(serde::Serialize, serde::Deserialize, sqlx::FromRow)]
pub struct SystemHealth {
    pub service: String,
    pub status: String,
    pub uptime: f64,
}

#[derive(serde::Serialize, serde::Deserialize, sqlx::FromRow)]
pub struct TelemetryEvent {
    pub event_id: uuid::Uuid,
    pub timestamp: chrono::DateTime<chrono::Utc>,
    pub service: String,
    pub event_type: String,
    pub severity: String,
}
```

---

## 🦀 STEP 8: CREATE RUST IPC COMMANDS

Create `src-tauri/src/commands.rs`:

```rust
use crate::database::{SystemHealth, TelemetryEvent};
use sqlx::PgPool;

#[tauri::command]
pub async fn get_system_health(pool: tauri::State<'_, PgPool>) -> Result<Vec<SystemHealth>, String> {
    // Mock data for now - replace with real queries
    let health = vec![
        SystemHealth {
            service: "dataforge".to_string(),
            status: "up".to_string(),
            uptime: 99.95,
        },
        SystemHealth {
            service: "neuroforge".to_string(),
            status: "up".to_string(),
            uptime: 99.87,
        },
        SystemHealth {
            service: "rake".to_string(),
            status: "up".to_string(),
            uptime: 98.42,
        },
    ];
    
    Ok(health)
}

#[tauri::command]
pub async fn get_recent_events(
    pool: tauri::State<'_, PgPool>,
    service: Option<String>,
    limit: Option<i64>,
) -> Result<Vec<TelemetryEvent>, String> {
    let limit = limit.unwrap_or(100);
    
    let query = match service {
        Some(svc) => {
            sqlx::query_as::<_, TelemetryEvent>(
                "SELECT event_id, timestamp, service, event_type, severity 
                 FROM events 
                 WHERE service = $1 
                 ORDER BY timestamp DESC 
                 LIMIT $2"
            )
            .bind(svc)
            .bind(limit)
        }
        None => {
            sqlx::query_as::<_, TelemetryEvent>(
                "SELECT event_id, timestamp, service, event_type, severity 
                 FROM events 
                 ORDER BY timestamp DESC 
                 LIMIT $1"
            )
            .bind(limit)
        }
    };
    
    query
        .fetch_all(pool.inner())
        .await
        .map_err(|e| e.to_string())
}
```

---

## 🦀 STEP 9: UPDATE RUST MAIN.RS

Edit `src-tauri/src/main.rs`:

```rust
// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod database;
mod commands;

use database::create_pool;
use commands::{get_system_health, get_recent_events};

#[tokio::main]
async fn main() {
    // Load environment variables
    dotenv::dotenv().ok();
    
    // Create database connection pool
    let pool = create_pool()
        .await
        .expect("Failed to create database pool");
    
    tauri::Builder::default()
        .manage(pool)
        .invoke_handler(tauri::generate_handler![
            get_system_health,
            get_recent_events
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

---

## 🎨 STEP 10: CREATE OVERVIEW DASHBOARD

Create `src/routes/+page.svelte`:

```svelte
<script lang="ts">
  import { invoke } from '@tauri-apps/api/tauri';
  import { onMount } from 'svelte';
  
  interface SystemHealth {
    service: string;
    status: string;
    uptime: number;
  }
  
  let healthData: SystemHealth[] = [];
  let loading = true;
  
  async function loadHealth() {
    try {
      healthData = await invoke<SystemHealth[]>('get_system_health');
      loading = false;
    } catch (error) {
      console.error('Failed to load health:', error);
      loading = false;
    }
  }
  
  onMount(() => {
    loadHealth();
    // Refresh every 30 seconds
    const interval = setInterval(loadHealth, 30000);
    return () => clearInterval(interval);
  });
  
  function getServiceColor(service: string): string {
    switch(service) {
      case 'dataforge': return 'text-dataforge-blue';
      case 'neuroforge': return 'text-neuroforge-violet';
      case 'rake': return 'text-rake-cyan';
      default: return 'text-white';
    }
  }
</script>

<div class="p-8">
  <!-- Header -->
  <div class="mb-8">
    <h1 class="text-4xl font-display text-forge-ember mb-2">FORGE COMMAND</h1>
    <p class="text-forge-steel">Unified Intelligence. Central Control.</p>
  </div>
  
  <!-- System Health -->
  <div class="mb-8">
    <h2 class="text-2xl font-semibold mb-4">System Health</h2>
    
    {#if loading}
      <div class="text-forge-steel">Loading...</div>
    {:else}
      <div class="grid grid-cols-3 gap-4">
        {#each healthData as service}
          <div class="kpi-card">
            <div class="flex items-center justify-between mb-2">
              <h3 class="text-lg font-semibold {getServiceColor(service.service)}">
                {service.service.toUpperCase()}
              </h3>
              <span class="status-badge {service.status}">
                {service.status.toUpperCase()}
              </span>
            </div>
            <div class="text-3xl font-bold">{service.uptime.toFixed(2)}%</div>
            <div class="text-sm text-forge-steel mt-1">Uptime</div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
  
  <!-- Navigation -->
  <div class="grid grid-cols-3 gap-4">
    <a href="/dataforge" class="panel p-6 hover:border-dataforge-blue transition-colors">
      <h3 class="text-xl font-semibold text-dataforge-blue mb-2">DataForge</h3>
      <p class="text-forge-steel text-sm">Vector memory analytics</p>
    </a>
    
    <a href="/neuroforge" class="panel p-6 hover:border-neuroforge-violet transition-colors">
      <h3 class="text-xl font-semibold text-neuroforge-violet mb-2">NeuroForge</h3>
      <p class="text-forge-steel text-sm">Model performance metrics</p>
    </a>
    
    <a href="/rake" class="panel p-6 hover:border-rake-cyan transition-colors">
      <h3 class="text-xl font-semibold text-rake-cyan mb-2">Rake</h3>
      <p class="text-forge-steel text-sm">Ingestion pipeline status</p>
    </a>
  </div>
</div>
```

---

## 📦 STEP 11: UPDATE PACKAGE.JSON SCRIPTS

Edit `package.json`:

```json
{
  "name": "forge-command",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "vite dev",
    "build": "vite build",
    "preview": "vite preview",
    "tauri": "tauri",
    "tauri:dev": "tauri dev",
    "tauri:build": "tauri build"
  },
  "devDependencies": {
    "@sveltejs/adapter-static": "^3.0.0",
    "@sveltejs/kit": "^2.0.0",
    "@sveltejs/vite-plugin-svelte": "^3.0.0",
    "@tauri-apps/cli": "^2.0.0",
    "@tauri-apps/api": "^2.0.0",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32",
    "svelte": "^4.2.7",
    "tailwindcss": "^3.3.6",
    "typescript": "^5.3.3",
    "vite": "^5.0.0"
  },
  "dependencies": {
    "chart.js": "^4.4.1",
    "date-fns": "^3.0.6",
    "lucide-svelte": "^0.300.0",
    "svelte-chartjs": "^3.1.4"
  },
  "type": "module"
}
```

---

## ⚙️ STEP 12: CONFIGURE SVELTE FOR TAURI

Edit `svelte.config.js`:

```javascript
import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  
  kit: {
    adapter: adapter({
      pages: 'build',
      assets: 'build',
      fallback: 'index.html',
      precompress: false,
      strict: true
    })
  }
};

export default config;
```

---

## ⚙️ STEP 13: UPDATE TAURI CONFIG

Edit `src-tauri/tauri.conf.json`:

```json
{
  "$schema": "https://schema.tauri.app/config/2",
  "productName": "Forge Command",
  "version": "0.1.0",
  "identifier": "com.boswell.forgecommand",
  "build": {
    "beforeDevCommand": "npm run dev",
    "beforeBuildCommand": "npm run build",
    "devUrl": "http://localhost:5173",
    "frontendDist": "../build"
  },
  "app": {
    "windows": [
      {
        "title": "Forge Command",
        "width": 1400,
        "height": 900,
        "resizable": true,
        "fullscreen": false,
        "decorations": true,
        "theme": "Dark"
      }
    ],
    "security": {
      "csp": null
    }
  },
  "bundle": {
    "active": true,
    "targets": "all",
    "icon": [
      "icons/32x32.png",
      "icons/128x128.png",
      "icons/128x128@2x.png",
      "icons/icon.icns",
      "icons/icon.ico"
    ]
  }
}
```

---

## 🔧 STEP 14: CREATE .ENV FILE

Create `.env` in ForgeCommand root:

```bash
DATABASE_URL=postgresql://localhost:5432/dataforge
```

---

## 🚀 STEP 15: RUN THE APP

```bash
# Make sure DataForge is running first
cd ~/projects/Coding2025/Forge/DataForge
source venv/bin/activate
python -m uvicorn app.main:app --port 8001

# In another terminal, run Forge Command
cd ~/projects/Coding2025/Forge/ForgeCommand
npm run tauri:dev
```

---

## ✅ VERIFICATION

If everything works, you should see:
1. ✅ Tauri window opens
2. ✅ Dark background (forge-black)
3. ✅ "FORGE COMMAND" title in ember color
4. ✅ Three service health cards (blue, violet, cyan)
5. ✅ 99%+ uptime shown (mock data)
6. ✅ Three navigation cards for each service

---

## 📁 FINAL DIRECTORY STRUCTURE

```
ForgeCommand/
├── src/
│   ├── routes/
│   │   ├── +layout.svelte
│   │   ├── +page.svelte
│   │   ├── dataforge/
│   │   │   └── +page.svelte
│   │   ├── neuroforge/
│   │   │   └── +page.svelte
│   │   └── rake/
│   │       └── +page.svelte
│   ├── lib/
│   │   └── components/
│   │       ├── StatusBadge.svelte
│   │       ├── KPICard.svelte
│   │       └── Chart.svelte
│   └── app.css
├── src-tauri/
│   ├── src/
│   │   ├── main.rs
│   │   ├── commands.rs
│   │   └── database.rs
│   ├── Cargo.toml
│   └── tauri.conf.json
├── package.json
├── svelte.config.js
├── tailwind.config.js
├── vite.config.ts
└── .env
```

---

## 🐛 TROUBLESHOOTING

### "Failed to create database pool"
```bash
# Check DATABASE_URL is set
echo $DATABASE_URL

# Verify DataForge is running
curl http://localhost:8001/health

# Check PostgreSQL is accessible
psql postgresql://localhost:5432/dataforge
```

### "Module not found: @tauri-apps/api"
```bash
npm install @tauri-apps/api
```

### "Rust compilation errors"
```bash
# Update Rust
rustup update

# Clean and rebuild
cd src-tauri
cargo clean
cargo build
```

### Window doesn't open
- Check console for errors
- Verify port 5173 is not in use
- Check tauri.conf.json devUrl

---

## 🎯 NEXT STEPS

Now that you have the foundation:

1. **Add more IPC commands** (get_dataforge_metrics, get_neuroforge_models, etc.)
2. **Create dashboard pages** (/dataforge, /neuroforge, /rake)
3. **Add charts** (Chart.js for time-series, bar charts)
4. **Implement real queries** (replace mock data with actual database queries)
5. **Add system tray** (see Tauri docs for tray-icon feature)
6. **Add notifications** (see Tauri docs for notification-all feature)

---

**You now have a working Tauri app with Forge styling!** 🚀

The CSS, colors, and dark mode are all configured. You can now build out the dashboards.
