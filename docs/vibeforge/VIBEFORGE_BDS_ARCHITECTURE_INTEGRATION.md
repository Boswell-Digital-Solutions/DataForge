# VibeForge_BDS: Forge Architecture Studio Integration

**How to Add Forge Architecture Visualization to VibeForge_BDS**

**Version:** 1.0  
**Status:** Ready for Implementation  
**Estimated Time:** 4-6 hours  

---

## 🎯 **Strategic Purpose**

The Forge Architecture Studio serves as the **internal reference dashboard** for the engineering team.

**Core Functions:**
1. **Architecture Reference** - Understanding the full Forge Ecosystem structure
2. **Service Discovery** - Finding ports, versions, contracts for all 15 services
3. **Pipeline Documentation** - Visual reference for M.A.P.O., NeuroForge, DataForge workflows
4. **Dependency Rules** - Understanding what can call what (governance enforcement)
5. **Contract Explorer** - Interactive API contracts for each service
6. **Onboarding Tool** - New developers understand system in 10 minutes

**Why In VibeForge_BDS:**
- Internal-only tool (not for public)
- Engineers need this reference constantly
- Visual + interactive > static documentation
- Contracts are source of truth for integrations

---

## 🏗️ **Integration Architecture**

### **Where It Lives**

```
VibeForge_BDS
├── Dashboard (main)
├── Skills Library
├── Planning
├── Execution
├── Evaluation
├── Coordination
├── System Logs
├── [NEW] Forge Architecture Studio  ← Add here
└── Settings
```

### **New Route Structure**

```
src/routes/vibeforge-bds/
├── +page.svelte                    (Dashboard overview)
├── architecture/
│   ├── +page.svelte                (Main architecture view)
│   ├── +layout.svelte              (Shared layout for section)
│   ├── lib/
│   │   ├── ArchitectureStudio.svelte (Converted from React)
│   │   ├── TierDiagram.svelte       (3-tier visualization)
│   │   ├── PipelineContracts.svelte (Pipeline details)
│   │   ├── DependencyRules.svelte   (Allowed/forbidden flows)
│   │   ├── ContractModal.svelte     (Interactive contract explorer)
│   │   └── types.ts                 (Shared types/contracts)
│   └── [service]/
│       └── +page.svelte            (Individual service detail)
├── skills/
├── planning/
├── execution/
├── evaluation/
├── coordination/
├── logs/
└── settings/
```

---

## 🎨 **Design System Integration**

### **Apply VibeForge_BDS Styling**

**Color Mapping (React → BDS):**

```javascript
// Original (React component)
const theme = {
  gold: '#fbbf24',
  ember: '#f97316',
  provider: { bg: '#1a1a2e', border: '#4a4a6a', accent: '#6366f1' },
  intelligence: { bg: '#1e3a5f', border: '#3b82f6' },
  consumer: { bg: '#2d1b3d', border: '#a855f7' }
}

// VibeForge_BDS (Svelte)
const theme = {
  brass: '#C19745',           // Primary accent (replace gold)
  violet: '#7B5FF1',          // Secondary accent (use for highlights)
  provider: {                 // AI Engines tier
    bg: 'rgba(193, 151, 69, 0.05)',
    border: 'rgba(193, 151, 69, 0.15)',
    accent: '#C19745'
  },
  intelligence: {             // Intelligence modules tier
    bg: 'rgba(123, 95, 241, 0.05)',
    border: 'rgba(123, 95, 241, 0.15)',
    accent: '#7B5FF1'
  },
  consumer: {                 // Consumer apps tier
    bg: 'rgba(106, 135, 166, 0.05)',
    border: 'rgba(106, 135, 166, 0.15)',
    accent: '#6A87A6'
  }
}
```

**Typography:**
- Headings: Cinzel Light (already loaded)
- Service names: Inter Medium
- Code/ports: JetBrains Mono

**Spacing:**
- Padding: 12px (tight)
- Gaps: 12px (grid-aligned)
- Border radius: 4-6px (sharp)

---

## 🔄 **Conversion: React → Svelte**

### **Step 1: Convert Main Component**

**File:** `src/lib/components/ArchitectureStudio.svelte`

```svelte
<script>
  import { onMount } from 'svelte';
  import TierDiagram from './architecture/TierDiagram.svelte';
  import PipelineContracts from './architecture/PipelineContracts.svelte';
  import DependencyRules from './architecture/DependencyRules.svelte';
  import ContractModal from './architecture/ContractModal.svelte';
  
  // State
  let activeTab = 'tiers';
  let showContracts = null;
  let darkMode = true; // Always dark in BDS
  let callTraceActive = false;
  let callTraceStep = 0;

  // Theme (BDS colors)
  const theme = {
    bg: '#1B1E24',
    surface: '#2A2D33',
    border: 'rgba(193, 151, 69, 0.15)',
    text: '#F5F6F7',
    textMuted: '#8A8F99',
    brass: '#C19745',
    violet: '#7B5FF1',
    provider: {
      bg: 'rgba(193, 151, 69, 0.05)',
      border: 'rgba(193, 151, 69, 0.15)',
      accent: '#C19745'
    },
    intelligence: {
      bg: 'rgba(123, 95, 241, 0.05)',
      border: 'rgba(123, 95, 241, 0.15)',
      accent: '#7B5FF1'
    },
    consumer: {
      bg: 'rgba(106, 135, 166, 0.05)',
      border: 'rgba(106, 135, 166, 0.15)',
      accent: '#6A87A6'
    }
  };

  // Service definitions (from original JSX)
  const services = {
    neuroforge: {
      name: 'NeuroForge',
      port: '8000',
      version: 'v1.0 API',
      tier: 'provider',
      category: 'ai-engines',
      status: 'production',
      description: 'AI orchestration & model routing'
    },
    mapo: {
      name: 'M.A.P.O.',
      port: '8003',
      version: 'v1.0 Pipeline',
      tier: 'provider',
      category: 'ai-engines',
      status: 'production',
      description: 'Multi-AI Pipeline Orchestrator'
    },
    dataforge: {
      name: 'DataForge',
      port: '8001',
      version: 'v5.2 API',
      tier: 'provider',
      category: 'knowledge',
      status: 'production',
      description: 'Vector storage & semantic search'
    },
    rake: {
      name: 'Rake',
      port: '8002',
      version: 'v1.0',
      tier: 'provider',
      category: 'knowledge',
      status: 'production',
      description: '5-stage ingestion pipeline'
    },
    forgeagents: {
      name: 'ForgeAgents',
      port: '8004',
      version: 'v0.9 Preview',
      tier: 'provider',
      category: 'ai-engines',
      status: 'beta',
      description: 'Autonomous agent orchestration'
    }
  };

  // Pipeline contracts (from original)
  const pipelines = {
    mapo: {
      name: 'M.A.P.O. Pipeline',
      stages: ['Initial', 'Review', 'Refinement', 'Final'],
      contract: {
        request: {
          pipeline_version: 'string',
          pipeline_id: 'uuid',
          // ... full contract from original
        }
      }
    },
    // ... other pipelines
  };

  // Export functions
  function exportToSVG() {
    // Export diagram as SVG
  }

  function exportToMermaid() {
    // Export as Mermaid diagram
  }

  function exportToJSON() {
    // Export contracts as JSON
  }
</script>

<div class="architecture-studio" style="background: {theme.bg}; color: {theme.text}">
  {/* Header */}
  <div class="header">
    <h1 class="heading-2">
      <span style="color: {theme.brass}">Forge</span> Architecture Studio
    </h1>
    <p class="text-secondary">Internal reference v3 — BDS-SAS</p>
  </div>

  {/* Navigation */}
  <div class="tabs">
    <button
      class="tab"
      class:active={activeTab === 'tiers'}
      on:click={() => (activeTab = 'tiers')}
      style="--accent-color: {theme.brass}"
    >
      3-Tier Architecture
    </button>
    <button
      class="tab"
      class:active={activeTab === 'pipelines'}
      on:click={() => (activeTab = 'pipelines')}
      style="--accent-color: {theme.brass}"
    >
      Pipeline Contracts
    </button>
    <button
      class="tab"
      class:active={activeTab === 'deps'}
      on:click={() => (activeTab = 'deps')}
      style="--accent-color: {theme.brass}"
    >
      Dependency Rules
    </button>
  </div>

  {/* Export Buttons */}
  <div class="export-buttons">
    <button on:click={exportToSVG} title="Export as SVG">📥 SVG</button>
    <button on:click={exportToJSON} title="Export as JSON">📋 JSON</button>
    <button on:click={exportToMermaid} title="Export as Mermaid">🧜 Mermaid</button>
  </div>

  {/* Content Tabs */}
  <div class="content">
    {#if activeTab === 'tiers'}
      <TierDiagram {theme} {services} />
    {/if}
    {#if activeTab === 'pipelines'}
      <PipelineContracts {theme} {pipelines} on:show-contract={(e) => (showContracts = e.detail)} />
    {/if}
    {#if activeTab === 'deps'}
      <DependencyRules {theme} />
    {/if}
  </div>

  {/* Contract Modal */}
  {#if showContracts}
    <ContractModal {theme} service={showContracts} on:close={() => (showContracts = null)} />
  {/if}
</div>

<style>
  .architecture-studio {
    padding: 24px;
    border-radius: 6px;
  }

  .header {
    text-align: center;
    margin-bottom: 24px;
  }

  h1 {
    margin: 0 0 8px 0;
    font-size: 28px;
  }

  .tabs {
    display: flex;
    gap: 12px;
    margin-bottom: 24px;
    padding: 12px;
    background: rgba(193, 151, 69, 0.05);
    border-radius: 6px;
  }

  .tab {
    padding: 10px 16px;
    border: none;
    background: transparent;
    color: #8A8F99;
    cursor: pointer;
    border-radius: 4px;
    font-weight: 500;
    transition: all 0.15s;
  }

  .tab.active {
    background: var(--accent-color);
    color: #1B1E24;
  }

  .export-buttons {
    display: flex;
    gap: 8px;
    margin-bottom: 24px;
  }

  .export-buttons button {
    padding: 8px 12px;
    background: rgba(193, 151, 69, 0.1);
    border: 1px solid rgba(193, 151, 69, 0.15);
    color: #F5F6F7;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    transition: all 0.15s;
  }

  .export-buttons button:hover {
    background: rgba(193, 151, 69, 0.2);
  }

  .content {
    background: #2A2D33;
    border: 1px solid rgba(193, 151, 69, 0.15);
    border-radius: 6px;
    padding: 24px;
  }
</style>
```

---

## 📊 **Integration Points with VibeForge_BDS**

### **1. Sidebar Navigation**

Add to `src/lib/components/Sidebar.svelte`:

```svelte
<nav class="sidebar-nav">
  {#each navItems as item}
    <!-- existing items -->
  {/each}
  
  {/* NEW: Architecture section */}
  <div class="nav-section">
    <div class="nav-section-title">Reference</div>
    <a href="/vibeforge-bds/architecture" class="sidebar-nav-item">
      <span class="icon">🏗️</span>
      <span class="label">Architecture Studio</span>
    </a>
  </div>
</nav>
```

### **2. Dashboard Overview Card**

Add to dashboard `src/routes/vibeforge-bds/+page.svelte`:

```svelte
<Panel title="Architecture Reference" icon="🏗️">
  <div class="architecture-preview">
    <p class="text-secondary">15 Core Services • 3 Tiers • 5 Pipelines</p>
    <div class="services-grid">
      <div class="service-badge">NeuroForge</div>
      <div class="service-badge">M.A.P.O.</div>
      <div class="service-badge">DataForge</div>
      <div class="service-badge">Rake</div>
      <div class="service-badge">ForgeAgents</div>
    </div>
    <Button href="/vibeforge-bds/architecture" variant="primary">
      View Full Architecture
    </Button>
  </div>
</Panel>
```

### **3. Service Details Pages**

**File:** `src/routes/vibeforge-bds/architecture/[service]/+page.svelte`

For each service (NeuroForge, DataForge, Rake, etc.):
- Service description
- API port & version
- Contract specification
- Dependency map
- Health status
- Recent metrics

---

## 🔌 **Live Data Integration (Optional)**

### **Connect to ForgeCommand Metrics**

The Architecture Studio can display **real-time status** from ForgeCommand:

```svelte
<script>
  import { onMount } from 'svelte';

  let serviceStatus = {};

  onMount(async () => {
    // Call ForgeCommand API
    const response = await fetch('/api/forgecommand/services/status');
    serviceStatus = await response.json();
  });
</script>

<!-- Show live status -->
<div class="service-status">
  {#each services as service}
    <div class="status-indicator">
      <span class="dot" style="background: {serviceStatus[service.name]?.status === 'healthy' ? '#49C883' : '#E8A64D'}"></span>
      <span>{service.name}</span>
    </div>
  {/each}
</div>
```

---

## 📋 **Implementation Roadmap**

### **Phase 1: Basic Integration (2-3 hours)**

- [ ] Convert React JSX to Svelte component
- [ ] Apply VibeForge_BDS design system colors
- [ ] Add to sidebar navigation
- [ ] Create main architecture page
- [ ] Verify tabs (Tiers, Pipelines, Dependencies) work

**Result:** Architecture Studio accessible in VibeForge_BDS

### **Phase 2: Design Polish (1-2 hours)**

- [ ] Apply Cinzel fonts to headings
- [ ] Use JetBrains Mono for service names/ports
- [ ] Adjust spacing (12px grid)
- [ ] Add brass accent borders
- [ ] Dark mode refinement
- [ ] Hover states with brass highlights

**Result:** Polished, professional appearance

### **Phase 3: Interactive Features (1 hour)**

- [ ] Contract modal explorer (click services to see contracts)
- [ ] Export to Mermaid/PlantUML/SVG
- [ ] Dependency visualization
- [ ] Call trace animation

**Result:** Interactive reference tool

### **Phase 4: Live Data (1-2 hours, Optional)**

- [ ] Connect to ForgeCommand API
- [ ] Show real-time service status
- [ ] Display version tracking
- [ ] Metric integration

**Result:** Living documentation dashboard

---

## 🎯 **Where This Fits in VibeForge_BDS**

```
VibeForge_BDS Main Dashboard
│
├─ Execution Metrics Dashboard
│  └─ Real-time skill execution, SAS compliance, PAORT status
│
├─ Skills Library
│  └─ Browse 120 skills, execute, view contracts
│
├─ Planning Module
│  └─ Plan upcoming work, sprints, roadmap
│
├─ Execution Module
│  └─ Run skills, monitor execution
│
├─ Evaluation Module
│  └─ Review results, compliance checks
│
├─ Coordination Module
│  └─ Multi-skill workflows, orchestration
│
├─ System Logs
│  └─ Complete execution history
│
├─ [NEW] ARCHITECTURE STUDIO  ← YOU ARE HERE
│  ├─ 3-Tier Architecture View
│  ├─ Pipeline Contracts Explorer
│  ├─ Dependency Rules Reference
│  └─ Service Details Pages
│
└─ Settings
   └─ Configuration, API keys
```

---

## 💡 **Why This Matters**

**Without Architecture Studio:**
- Developers don't understand system structure
- Finding service ports requires digging code
- Contract specs scattered across repos
- Onboarding takes weeks
- Dependency rules unclear

**With Architecture Studio in VibeForge_BDS:**
- ✅ System structure is visible & interactive
- ✅ Service discovery in one place
- ✅ Contracts are always accessible
- ✅ New developers onboard in minutes
- ✅ Dependency rules enforced visually
- ✅ Governance is transparent

---

## 🚀 **Quick Start**

### **Step 1: Set Up Component (30 min)**

```bash
# Create architecture directory
mkdir -p src/routes/vibeforge-bds/architecture/lib

# Create main component
touch src/routes/vibeforge-bds/architecture/+page.svelte
touch src/lib/components/ArchitectureStudio.svelte
```

### **Step 2: Copy Content (30 min)**

Copy the service/pipeline/contract data from the React component into Svelte structures.

### **Step 3: Apply BDS Design (1 hour)**

- Update colors (gold → brass, adjust tier colors)
- Apply typography (Cinzel, Inter, JetBrains Mono)
- Adjust spacing (12px grid)
- Add brass borders

### **Step 4: Integrate into Dashboard (30 min)**

- Add navigation link to sidebar
- Add preview card to dashboard
- Test navigation

### **Step 5: Polish & Deploy (1 hour)**

- Test all tabs
- Verify exports work
- Cross-browser test
- Deploy

---

## 📦 **Files to Create/Modify**

```
src/routes/vibeforge-bds/
├── architecture/
│   ├── +page.svelte                    [CREATE]
│   ├── +layout.svelte                  [CREATE]
│   └── lib/
│       ├── ArchitectureStudio.svelte    [CREATE]
│       ├── TierDiagram.svelte           [CREATE]
│       ├── PipelineContracts.svelte     [CREATE]
│       ├── DependencyRules.svelte       [CREATE]
│       ├── ContractModal.svelte         [CREATE]
│       └── types.ts                     [CREATE]
│
├── +page.svelte                        [MODIFY - add preview card]
└── ../Sidebar.svelte                   [MODIFY - add nav link]
```

---

## ✅ **Success Criteria**

When complete:

✓ Architecture page accessible via sidebar  
✓ 3-Tier architecture displays correctly  
✓ Pipeline contracts tab shows all 5 pipelines  
✓ Dependency rules are visible & interactive  
✓ Can click services to see contracts  
✓ Can export to SVG/JSON/Mermaid  
✓ BDS design system fully applied  
✓ Dark mode only (consistent with VibeForge_BDS)  
✓ Cinzel/Inter/JetBrains Mono fonts loaded  
✓ Brass accent colors throughout  
✓ 12px spacing grid maintained  

---

## 🎬 **Suggested Implementation Flow**

1. **Use Claude Code prompt** (if available):
   - Copy architecture conversion prompt
   - Execute in VS Code
   - Automated conversion + integration

2. **Or Manual**: Follow Phase 1-4 above sequentially

3. **Test**: Run `npm run dev`, navigate to `/vibeforge-bds/architecture`

4. **Deploy**: Commit and push to production

---

## 📞 **What You Get**

A **complete internal reference tool** for the engineering team that:
- Shows the entire Forge Ecosystem visually
- Enables service discovery
- Documents pipeline contracts
- Enforces dependency rules
- Helps with onboarding
- Guides architectural decisions
- Integrates with VibeForge_BDS dashboard

**Total time to implement:** 4-6 hours  
**Maintenance required:** Minimal (auto-generated from contracts)  
**Team impact:** High (becomes go-to reference)

---

**Ready to integrate?** Start with Phase 1 (convert React → Svelte) or use Claude Code for automated conversion. 🚀
