# CORTEX - VS Code Implementation Context

## Core Identity
**What:** AI-powered local-first file intelligence system  
**Why:** Knowledge workers waste 2.5+ hours/week finding files  
**How:** Rust/Tauri + SvelteKit with semantic search + smart organization  
**Differentiator:** Local privacy + AI power + professional UX (no competitor has all three)

## Tech Stack (Non-Negotiable)

### Backend (Rust)
```toml
# Core dependencies
tokio = "1"                    # Async runtime
rusqlite = "0.31"             # Database (SQLite + FTS5)
notify = "6.0"                # Filesystem watching
tantivy = "0.21"              # Full-text search
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"

# Content extraction
docx-rs = "0.4"
pdf-extract = "0.7"
pulldown-cmark = "0.9"
image = "0.24"

# AI/ML
ort = "1.16"                  # ONNX Runtime (local embeddings)
reqwest = "0.11"              # For NeuroForge API
```

### Frontend (SvelteKit + Tauri)
```json
{
  "@tauri-apps/api": "^2.0.0",
  "svelte": "^4.0.0",
  "@sveltejs/kit": "^2.0.0",
  "tailwindcss": "^3.4.0",
  "lucide-svelte": "^0.300.0"
}
```

### Database (SQLite)
- Location: `~/.cortex/db.sqlite`
- WAL mode for concurrency
- FTS5 for full-text search
- Memory-mapped I/O

## Architecture Pattern

```
TAURI APP
├── Frontend (SvelteKit)
│   ├── Search Bar (global, Cmd+K)
│   ├── Sidebar (navigation)
│   ├── Main Content (grid/list)
│   └── Preview Panel (progressive disclosure)
│
├── Backend Core (Rust)
│   ├── Indexing Pipeline
│   │   ├── File Scanner → Watcher → Priority Queue
│   │   ├── Content Extractor → Chunker
│   │   ├── Embedding Generator → Vector Store
│   │   └── Auto-Tagger → Database
│   │
│   ├── Search Engine
│   │   ├── Query Parser
│   │   ├── FTS Search ──┐
│   │   ├── Vector Search ┼→ Hybrid Fusion → Ranker
│   │   └── Filter Engine ┘
│   │
│   └── Smart Features
│       ├── Smart Collections
│       ├── Duplicate Detector
│       ├── Cleanup Analyzer
│       └── Related Files Finder
│
└── Database (SQLite + FTS5)
    ├── files, file_content, files_fts
    ├── embeddings, tags, file_tags
    ├── smart_collections
    └── duplicate_groups
```

## Critical Database Schema

```sql
-- Core tables only - full schema in main doc
CREATE TABLE files (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    size INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL,
    modified_at TIMESTAMP NOT NULL,
    last_indexed TIMESTAMP NOT NULL,
    hash TEXT,
    root_path TEXT NOT NULL,
    is_deleted BOOLEAN DEFAULT 0
);

CREATE TABLE file_content (
    file_id INTEGER PRIMARY KEY,
    text_content TEXT,
    word_count INTEGER,
    summary TEXT,
    FOREIGN KEY (file_id) REFERENCES files(id)
);

CREATE TABLE embeddings (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding BLOB NOT NULL,        -- 384D vector
    chunk_index INTEGER NOT NULL,
    FOREIGN KEY (file_id) REFERENCES files(id)
);

CREATE VIRTUAL TABLE files_fts USING fts5(
    filename,
    content,
    content='file_content',
    content_rowid='file_id'
);
```

## Key Implementation Patterns

### 1. Tauri Command Pattern
```rust
#[command]
async fn search_files(
    query: String,
    filters: Option<SearchFilters>,
    search_type: Option<String>,
    limit: usize,
    offset: usize,
    state: State<'_, AppState>
) -> Result<SearchResults, String> {
    // Implementation
}
```

### 2. Progressive Indexing
```rust
enum IndexPriority {
    Immediate,  // < 1MB, recently modified
    High,       // < 10MB
    Normal,     // < 100MB
    Low,        // > 100MB
}

// Process by priority, yield to UI
```

### 3. Hybrid Search Fusion
```rust
async fn search_hybrid(query: &str) -> Result<Vec<FileResult>> {
    // 1. FTS search (fast)
    let fts_results = fts_search(query).await?;
    
    // 2. Semantic search (accurate)
    let semantic_results = vector_search(query).await?;
    
    // 3. Reciprocal Rank Fusion
    let fused = rrf_fusion(fts_results, semantic_results);
    
    Ok(fused)
}
```

### 4. Error Handling Pattern
```rust
#[derive(Debug, Serialize)]
enum CortexError {
    PermissionDenied { path: String, suggestion: String },
    DiskFull { required: u64, available: u64 },
    ExtractionFailed { path: PathBuf, error: String },
    DatabaseLocked,
    SearchTimeout,
}

// Always return user-friendly messages
impl fmt::Display for CortexError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Self::PermissionDenied { path, suggestion } => {
                write!(f, "Cannot access {}\n\n→ {}", path, suggestion)
            }
            // ...
        }
    }
}
```

## Performance Budget

```
Startup:          < 2s (cold start)
Search (keyword): < 100ms
Search (semantic):< 500ms
UI Response:      60 FPS
Indexing:         > 50 files/sec (small files)
Memory (idle):    < 150MB
Memory (peak):    < 500MB
```

## UX Design Tokens

```css
/* Core colors - Neural Gold theme */
--cortex-black: #0A0A0C;
--cortex-deep: #0E0F12;
--slate-byte: #15161A;
--neural-gold: #C9A46C;
--ember-gold: #F3C87D;
--silver-neural: #CCCCD6;

/* Typography */
--font-primary: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto;
--text-base: 1rem;
--font-semibold: 600;

/* Spacing (4px base) */
--space-2: 0.5rem;
--space-4: 1rem;
--space-8: 2rem;
```

## Development Phases

### Phase 0: Foundation (Week 1-2)
**Goal:** Working indexer with basic search
- [x] Project setup
- [x] Database schema
- [x] File scanner + watcher
- [x] Content extractors
- [x] FTS search
- [x] CLI testing

**Success:** Index 10K files < 5min, search < 100ms

### Phase 1: Desktop UI (Week 3)
**Goal:** Tauri app with professional UX
- [ ] Tauri integration
- [ ] Main layout (sidebar, grid, preview)
- [ ] Search bar with suggestions
- [ ] Settings page
- [ ] First-run experience
- [ ] Dark theme

**Success:** App starts < 2s, feels professional

### Phase 2: AI Features (Week 4)
**Goal:** Semantic search + intelligence
- [ ] Local embedding generation (ONNX)
- [ ] Vector similarity search
- [ ] Hybrid search fusion
- [ ] Auto-tagging
- [ ] AI summaries
- [ ] Related files

**Success:** AI features accurate and fast

### Phase 3: Advanced Features (Week 5-6)
**Goal:** Smart Collections, cleanup, polish
- [ ] Smart Collections engine
- [ ] Duplicate detection
- [ ] Cleanup analyzer
- [ ] Command palette
- [ ] Bulk operations
- [ ] Export/backup

**Success:** All features production-ready

### Phase 4: Testing & Launch (Week 7-8)
- [ ] Unit + integration tests (90%+ coverage)
- [ ] Performance profiling
- [ ] Beta testing
- [ ] Documentation
- [ ] Marketing materials
- [ ] Launch

## Critical Anti-Patterns to Avoid

1. **Don't:** Index everything blindly
   **Do:** Priority-based indexing with user control

2. **Don't:** Block UI during indexing
   **Do:** Background processing with progress feedback

3. **Don't:** Send file content to cloud
   **Do:** Only embeddings (vectors) if cloud is enabled

4. **Don't:** Ignore edge cases (permissions, network drives, corruption)
   **Do:** Graceful degradation with helpful error messages

5. **Don't:** Over-engineer v1
   **Do:** Ship MVP, iterate based on real usage

## Testing Strategy

```rust
// Unit tests for core logic
#[test]
fn test_search_basic() { ... }

// Integration tests for full pipeline
#[tokio::test]
async fn test_full_indexing_pipeline() { ... }

// UI tests with Playwright
test('search shows results', async ({ page }) => { ... });

// Performance benchmarks
#[bench]
fn bench_search_performance(b: &mut Bencher) { ... }
```

## File Organization

```
cortex/
├── src-tauri/           # Rust backend
│   ├── src/
│   │   ├── main.rs
│   │   ├── commands/    # Tauri commands
│   │   ├── indexer/     # Indexing pipeline
│   │   ├── search/      # Search engine
│   │   ├── db/          # Database layer
│   │   └── ai/          # AI features
│   └── Cargo.toml
│
├── src/                 # SvelteKit frontend
│   ├── routes/
│   ├── lib/
│   │   ├── components/
│   │   └── stores/
│   └── app.css
│
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

## Key Commands Reference

### Tauri Commands (Rust → Frontend)
```rust
search_files(query, filters, type, limit, offset) -> SearchResults
get_file_detail(file_id) -> FileDetail
apply_tags(file_id, tag_ids) -> ()
create_collection(name, rules) -> i64
find_duplicates(match_type) -> Vec<DuplicateGroup>
start_indexing(paths) -> String
get_index_status() -> IndexStatus
```

### Keyboard Shortcuts
```
Cmd/Ctrl + K       → Focus search
Cmd/Ctrl + P       → Command palette
Enter              → Open selected file
Space              → Quick preview
Cmd/Ctrl + Shift + F → Advanced search
```

## Success Metrics

**Technical:**
- Index 10K files < 5 minutes
- Search results < 100ms (keyword), < 500ms (semantic)
- Startup < 2 seconds
- Memory < 150MB idle, < 500MB indexing
- 90%+ test coverage

**Business:**
- Year 1: 500-1,500 paid users
- 10-15% free → paid conversion
- 80%+ retention at 3 months
- NPS 50+

## Resources

- Main spec: `Cortex_Complete_Implementation_Plan.md` (full details)
- This doc: Quick reference for development
- Tauri docs: https://tauri.app
- SQLite FTS5: https://www.sqlite.org/fts5.html

---

**Use this as context when working with Claude in VS Code. The full implementation plan has all the details, but this gives you the essential patterns and decisions.**
