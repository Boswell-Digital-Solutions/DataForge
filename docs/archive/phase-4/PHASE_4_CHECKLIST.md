# Phase 4 Implementation Checklist & Status Tracker

**Project**: Forge Research Ecosystem - Phase 4 (Connectors & Export)  
**Status**: Ready to Begin ✅  
**Start Date**: November 20, 2025  
**Target Completion**: December 4-18, 2025 (2-4 weeks)  
**Team Size**: 1-2 developers

---

## 📋 Executive Checklist

### Phase 4 Overview

Phase 4 adds three new data source connectors (GitHub, Discord, RFC) plus advanced filtering and export functionality to the existing Forge system. This expands the research capabilities from 1 source (StackOverflow) to 4+ sources.

**Scope**:

- [x] GitHub Connector (issues + discussions)
- [x] Discord Connector (community discussions)
- [x] RFC Connector (RFC database search)
- [x] Advanced Filtering (date, author, language, score)
- [x] Export Functionality (markdown, PDF, JSON)
- [x] Performance Optimization (indexing, caching)

**Deliverables**:

- 3 new connector files (~750 lines Python)
- 2 updated service files (~100 lines)
- 2 new frontend components (~450 lines TypeScript/Svelte)
- Comprehensive tests (~500 lines)
- Complete documentation

---

## 🎯 Week 1: Core Connectors (4 Days)

### Day 1: GitHub Connector Implementation

**Objective**: Implement GitHub Issues/Discussions search  
**Files**: `DataForge/app/services/github_connector.py`  
**Time**: 3-4 hours  
**Guide**: `GITHUB_CONNECTOR_GUIDE.md`

#### Checklist

- [ ] Create `github_connector.py` file (300 lines)
- [ ] Implement `GitHubConnector` class
- [ ] Implement `_search_issues()` method
- [ ] Implement `_search_discussions()` method
- [ ] Implement `_format_issue_result()` method
- [ ] Implement rate limit tracking
- [ ] Add error handling and retries
- [ ] Write unit tests (50+ lines)
- [ ] Test with sample queries
- [ ] Document API usage

**Acceptance Criteria**:

- ✅ Searches GitHub issues successfully
- ✅ Returns up to 30 results
- ✅ Includes relevance scoring
- ✅ Handles errors gracefully
- ✅ Unit tests pass
- ✅ Rate limit info tracked

**Command Reference**:

```bash
# Run tests
cd DataForge && pytest tests/test_github_connector.py -v

# Manual test
export GITHUB_API_KEY=ghp_xxx
python -m app.services.github_connector
```

---

### Day 2: Discord Connector Implementation

**Objective**: Implement Discord community discussion search  
**Files**: `DataForge/app/services/discord_connector.py`  
**Time**: 2-3 hours  
**Guide**: `DISCORD_RFC_CONNECTORS_GUIDE.md`

#### Checklist

- [ ] Create `discord_connector.py` file (250 lines)
- [ ] Implement `DiscordConnector` class
- [ ] Implement `_search_guild()` method
- [ ] Implement `_format_message_result()` method
- [ ] Add user anonymization option
- [ ] Implement relevance scoring
- [ ] Add error handling
- [ ] Write unit tests (30+ lines)
- [ ] Test with sample servers
- [ ] Document configuration

**Acceptance Criteria**:

- ✅ Searches Discord messages successfully
- ✅ Works with multiple servers
- ✅ Anonymizes users when requested
- ✅ Handles permissions gracefully
- ✅ Unit tests pass
- ✅ Rate limiting respected

**Environment Setup**:

```bash
# Get bot token from https://discord.com/developers/applications
# Add to .env
DISCORD_BOT_TOKEN=your_token_here
DISCORD_SERVER_IDS=server_id_1,server_id_2
```

---

### Day 3: RFC Connector Implementation

**Objective**: Implement RFC database search  
**Files**: `DataForge/app/services/rfc_connector.py`  
**Time**: 1-2 hours  
**Guide**: `DISCORD_RFC_CONNECTORS_GUIDE.md`

#### Checklist

- [ ] Create `rfc_connector.py` file (200 lines)
- [ ] Implement `RFCConnector` class
- [ ] Load RFC metadata (static data)
- [ ] Implement full-text search
- [ ] Implement `_matches_query()` method
- [ ] Implement `_format_result()` method
- [ ] Add metadata extraction
- [ ] Write unit tests (40+ lines)
- [ ] Test with multiple queries
- [ ] Document RFC data structure

**Acceptance Criteria**:

- ✅ Searches RFC database successfully
- ✅ Finds relevant RFCs by title/abstract/keywords
- ✅ Includes metadata (author, year, status)
- ✅ Links to RFC archives
- ✅ Unit tests pass
- ✅ No external API calls

**Sample Queries to Test**:

```bash
python -c "
import asyncio
from app.services.rfc_connector import RFCConnector

async def test():
    rfc = RFCConnector()
    for q in ['HTTP', 'authentication', 'protocol', 'encryption']:
        results = await rfc.search(q, max_results=3)
        print(f'{q}: {len(results)} results')

asyncio.run(test())
"
```

---

### Day 4: Service Integration & Testing

**Objective**: Integrate all connectors and test end-to-end  
**Files**:

- `DataForge/app/services/external_search_service.py` (update)
- `DataForge/app/models/schemas.py` (update SourceType enum)

**Time**: 2-3 hours

#### Checklist

- [ ] Update `SourceType` enum with new sources
- [ ] Import all three new connectors
- [ ] Register connectors in `ExternalSearchService`
- [ ] Update `search_all()` method to use all connectors
- [ ] Add connector selection logic
- [ ] Test concurrent searches
- [ ] Performance test (timing)
- [ ] Error handling across all connectors
- [ ] Update external_search_router.py endpoints
- [ ] Integration tests pass

**Code Update Example**:

```python
# DataForge/app/models/schemas.py - Update enum
class SourceType(str, Enum):
    STACKOVERFLOW = "stackoverflow"
    GITHUB_ISSUE = "github_issue"          # NEW
    GITHUB_DISCUSSION = "github_discussion"  # NEW
    DISCORD = "discord"                    # NEW
    RFC = "rfc"                            # NEW

# DataForge/app/services/external_search_service.py - Register connectors
def __init__(self):
    self.connectors = {
        "stackoverflow": StackOverflowConnector(),
        "github": GitHubConnector(api_token=os.getenv("GITHUB_API_KEY")),
        "discord": DiscordConnector(
            bot_token=os.getenv("DISCORD_BOT_TOKEN"),
            server_ids=os.getenv("DISCORD_SERVER_IDS", "").split(",")
        ),
        "rfc": RFCConnector(),
    }
```

**Test Command**:

```bash
cd DataForge
pytest tests/test_external_search_service.py -v -k "test_search_all_sources"
```

**Acceptance Criteria**:

- ✅ All 4 connectors available
- ✅ Concurrent searches work
- ✅ Results properly formatted
- ✅ Errors handled gracefully
- ✅ Integration tests pass
- ✅ Performance acceptable (<3 sec for 4 sources)

---

## 🎯 Week 2: Integration & Testing (5 Days)

### Day 5-6: Comprehensive Testing

**Objective**: Test all functionality end-to-end  
**Time**: 4-5 hours

#### Unit Tests

- [ ] `tests/test_github_connector.py` (50+ lines)
- [ ] `tests/test_discord_connector.py` (40+ lines)
- [ ] `tests/test_rfc_connector.py` (40+ lines)
- [ ] `tests/test_external_search_service.py` (update, +50 lines)

#### Integration Tests

- [ ] Search all sources concurrently
- [ ] Verify result deduplication
- [ ] Check error handling
- [ ] Test rate limiting
- [ ] Verify result formatting
- [ ] Performance testing

#### Checklist

- [ ] Write GitHub connector tests
- [ ] Write Discord connector tests
- [ ] Write RFC connector tests
- [ ] Write integration tests
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] Coverage > 80%
- [ ] No critical bugs
- [ ] Performance acceptable
- [ ] Documentation updated

**Run All Tests**:

```bash
cd DataForge
pytest tests/ -v --cov=app --cov-report=html
# Coverage report in htmlcov/index.html
```

**Acceptance Criteria**:

- ✅ Unit test coverage > 80%
- ✅ Integration tests passing
- ✅ Zero critical bugs
- ✅ Performance < 3 seconds
- ✅ All connectors working independently
- ✅ All connectors working together

---

### Day 7-8: NeuroForge Integration

**Objective**: Update NeuroForge to use new data sources  
**Files**:

- `NeuroForge/services/research_orchestrator.py` (update)
- `NeuroForge/services/dataforge_client.py` (update)

**Time**: 2-3 hours

#### Checklist

- [ ] Update `dataforge_client.py` to use new sources
- [ ] Add source selection to NeuroForge API
- [ ] Update research_orchestrator.py
- [ ] Test NeuroForge integration
- [ ] Update API documentation
- [ ] Test with multiple sources
- [ ] Verify result quality
- [ ] Update README

**Example Update**:

```python
# NeuroForge/services/research_orchestrator.py
async def orchestrate(self, query: str, sources: List[str] = None):
    if sources is None:
        sources = ["stackoverflow", "github", "discord", "rfc"]

    # Call DataForge with specified sources
    results = await self.dataforge_client.search_external(
        query=query,
        sources=sources
    )
```

**Test Command**:

```bash
curl -X POST http://localhost:8002/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "OAuth2",
    "sources": ["github", "discord", "rfc"]
  }'
```

---

### Day 9: VibeForge Research Panel Updates

**Objective**: Add source selection UI to VibeForge  
**Files**: `vibeforge/src/lib/components/ResearchPanel.svelte` (update)

**Time**: 2-3 hours

#### Checklist

- [ ] Add source selection checkboxes
- [ ] Update ResearchPanel.svelte component
- [ ] Update researchStore.ts to track sources
- [ ] Test UI interactivity
- [ ] Update API calls to pass sources
- [ ] Style source selector
- [ ] Test with new sources
- [ ] Verify accessibility

**Component Update Example**:

```svelte
<!-- Source selector in ResearchPanel.svelte -->
<div class="sources">
  <label>
    <input type="checkbox" bind:checked={sources.github} />
    GitHub
  </label>
  <label>
    <input type="checkbox" bind:checked={sources.discord} />
    Discord
  </label>
  <label>
    <input type="checkbox" bind:checked={sources.rfc} />
    RFC
  </label>
</div>
```

---

## 🎯 Week 3: Frontend Enhancement (5 Days)

### Day 10-11: Advanced Filtering UI

**Objective**: Add filtering UI for date, author, language, score  
**Files**:

- `vibeforge/src/lib/components/FilterPanel.svelte` (new, 150 lines)
- `vibeforge/src/lib/stores/filterStore.ts` (new, 100 lines)
- `vibeforge/src/lib/components/ResearchPanel.svelte` (update)

**Time**: 3-4 hours

#### Checklist

- [ ] Create `FilterPanel.svelte` component
- [ ] Create `filterStore.ts` store
- [ ] Add date range picker
- [ ] Add author filter input
- [ ] Add language/framework selector
- [ ] Add score threshold slider
- [ ] Wire filters to API calls
- [ ] Test filtering functionality
- [ ] Style filter UI
- [ ] Update ResearchPanel.svelte

**Store Example**:

```typescript
// vibeforge/src/lib/stores/filterStore.ts
import { writable, derived } from "svelte/store";

export const filterState = writable({
  dateRange: { from: null, to: null },
  authors: [],
  languages: [],
  minScore: 0,
});

export const applyFilters = (filters) => {
  filterState.set(filters);
};
```

**Acceptance Criteria**:

- ✅ Date range picker working
- ✅ Author filter working
- ✅ Language filter working
- ✅ Score threshold working
- ✅ Filters applied to API calls
- ✅ Results update dynamically
- ✅ Filters persist (localStorage)
- ✅ UI accessible and responsive

---

### Day 12-13: Export Functionality

**Objective**: Add export to markdown, PDF, JSON, clipboard  
**Files**:

- `vibeforge/src/lib/components/ExportPanel.svelte` (new, 200 lines)
- `DataForge/app/api/export_router.py` (new, 100 lines)

**Time**: 3-4 hours

#### Checklist

- [ ] Create `ExportPanel.svelte` component
- [ ] Create `export_router.py` in DataForge
- [ ] Implement markdown export
- [ ] Implement PDF export
- [ ] Implement JSON export
- [ ] Implement copy to clipboard
- [ ] Add download button
- [ ] Test all export formats
- [ ] Style export UI
- [ ] Add success notifications

**Component Example**:

```svelte
<!-- vibeforge/src/lib/components/ExportPanel.svelte -->
<script>
  let format = 'markdown';

  async function exportResults() {
    const response = await fetch('/api/v1/export', {
      method: 'POST',
      body: JSON.stringify({ results: $researchStore.results, format })
    });

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `research-${Date.now()}.${format === 'markdown' ? 'md' : format}`;
    a.click();
  }
</script>

<div class="export">
  <select bind:value={format}>
    <option value="markdown">📄 Markdown</option>
    <option value="pdf">📑 PDF</option>
    <option value="json">📋 JSON</option>
  </select>
  <button on:click={exportResults}>Export</button>
</div>
```

**Backend Implementation**:

```python
# DataForge/app/api/export_router.py
from fastapi import APIRouter
from fpdf import FPDF
import json

router = APIRouter(prefix="/export", tags=["export"])

@router.post("/{format}")
async def export_results(results: List[SearchResult], format: str):
    if format == "markdown":
        return _export_markdown(results)
    elif format == "pdf":
        return _export_pdf(results)
    elif format == "json":
        return results  # Return as JSON
```

**Acceptance Criteria**:

- ✅ Markdown export working
- ✅ PDF export working (with formatting)
- ✅ JSON export working
- ✅ Copy to clipboard working
- ✅ Downloads with correct filename
- ✅ All formats properly formatted
- ✅ Large exports work (100+ results)
- ✅ Error handling for export failures

---

### Day 14: Performance Optimization & Polishing

**Objective**: Optimize performance and finalize implementation  
**Time**: 3-4 hours

#### Database Optimization

- [ ] Create indexes on search_results table
- [ ] Test query performance
- [ ] Optimize slow queries
- [ ] Add query analyzer

```sql
CREATE INDEX idx_search_query_hash ON search_results(query_hash);
CREATE INDEX idx_search_source ON search_results(source);
CREATE INDEX idx_search_created_at ON search_results(created_at DESC);
CREATE INDEX idx_search_author ON search_results(author);
CREATE INDEX idx_search_score ON search_results(relevance_score DESC);
```

#### Caching Layer

- [ ] Implement Redis caching for searches
- [ ] Test cache hit rate
- [ ] Set appropriate TTL
- [ ] Monitor cache effectiveness

```python
# Enhanced caching
async def search_all_cached(query: str, sources: List[str]):
    cache_key = f"search:{query}:{','.join(sorted(sources))}"

    # Check cache
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # Search
    results = await search_all(query, sources)

    # Cache for 1 hour
    await redis.setex(cache_key, 3600, json.dumps(results))

    return results
```

#### Final Polish

- [ ] Update all documentation
- [ ] Create Phase 4 completion report
- [ ] Review code for quality
- [ ] Performance testing
- [ ] Security audit
- [ ] Accessibility check
- [ ] User testing (if applicable)
- [ ] Create deployment checklist

**Performance Targets**:

- Query latency: < 2 seconds (uncached), < 100ms (cached)
- Cache hit rate: > 40%
- Throughput: > 50 queries/sec
- Database query time: < 100ms
- Memory usage: < 500MB

---

## 📊 Implementation Summary

### Code Statistics

| Component                | LOC        | Time       | Status |
| ------------------------ | ---------- | ---------- | ------ |
| **GitHub Connector**     | 300        | 3-4h       | [ ]    |
| **Discord Connector**    | 250        | 2-3h       | [ ]    |
| **RFC Connector**        | 200        | 1-2h       | [ ]    |
| **Service Updates**      | 100        | 1-2h       | [ ]    |
| **Unit Tests**           | 200        | 2-3h       | [ ]    |
| **Integration Tests**    | 150        | 1-2h       | [ ]    |
| **Filter UI**            | 250        | 3-4h       | [ ]    |
| **Export Functionality** | 300        | 3-4h       | [ ]    |
| **Documentation**        | 500        | 2-3h       | [ ]    |
| **Total**                | **2,250+** | **19-28h** | Ready  |

### Deliverables Checklist

**Backend**:

- [ ] `github_connector.py` - 300 lines
- [ ] `discord_connector.py` - 250 lines
- [ ] `rfc_connector.py` - 200 lines
- [ ] `external_search_service.py` - updated
- [ ] `export_router.py` - new endpoint
- [ ] Comprehensive tests - 400+ lines
- [ ] API documentation

**Frontend**:

- [ ] Source selector UI
- [ ] `FilterPanel.svelte` - 150 lines
- [ ] `ExportPanel.svelte` - 200 lines
- [ ] `filterStore.ts` - 100 lines
- [ ] Updated research integration
- [ ] Component tests

**Documentation**:

- [ ] `GITHUB_CONNECTOR_GUIDE.md` - 350 lines ✅ Created
- [ ] `DISCORD_RFC_CONNECTORS_GUIDE.md` - 400 lines ✅ Created
- [ ] `PHASE_4_IMPLEMENTATION_GUIDE.md` - 550 lines ✅ Created
- [ ] `PHASE_4_CHECKLIST.md` - this file ✅ Creating
- [ ] Updated API documentation
- [ ] Deployment guide

---

## 🚀 Getting Started

### 1. Setup Development Environment

```bash
cd /home/charles/projects/Coding2025/Forge

# Create feature branch
git checkout -b feature/phase-4-connectors

# Set environment variables
cp .env.example .env
# Edit .env and add:
# GITHUB_API_KEY=ghp_xxx
# DISCORD_BOT_TOKEN=xxx
# DISCORD_SERVER_IDS=xxx
```

### 2. Start with Day 1

```bash
# Create GitHub connector
touch DataForge/app/services/github_connector.py

# Copy implementation from GITHUB_CONNECTOR_GUIDE.md

# Run tests
cd DataForge
pytest tests/test_github_connector.py -v
```

### 3. Track Progress

Update this checklist as you complete each day:

```
Day 1: [ X ] GitHub Connector
Day 2: [   ] Discord Connector
Day 3: [   ] RFC Connector
Day 4: [   ] Service Integration
...
```

### 4. Daily Commits

```bash
# After each day
git add -A
git commit -m "feat(Phase4): implement github connector

- Add GitHubConnector class
- Implement issue search
- Add rate limiting
- Include unit tests"

git push origin feature/phase-4-connectors
```

---

## ✅ Success Criteria

### Phase 4 Complete When:

**Functionality**

- ✅ 4 data sources working (StackOverflow + GitHub + Discord + RFC)
- ✅ Advanced filtering working
- ✅ Export to multiple formats
- ✅ End-to-end flow working

**Performance**

- ✅ Query latency < 3 seconds
- ✅ Cache hit rate > 40%
- ✅ Database queries < 100ms
- ✅ Throughput > 50 queries/sec

**Quality**

- ✅ Test coverage > 80%
- ✅ Zero critical bugs
- ✅ All tests passing
- ✅ Code reviewed

**Documentation**

- ✅ API docs updated
- ✅ User guide created
- ✅ Deployment instructions
- ✅ Troubleshooting guide

---

## 📞 Reference

**Guides Created**:

- ✅ `PHASE_4_IMPLEMENTATION_GUIDE.md` (550 lines)
- ✅ `GITHUB_CONNECTOR_GUIDE.md` (350 lines)
- ✅ `DISCORD_RFC_CONNECTORS_GUIDE.md` (400 lines)
- ✅ `PHASE_4_CHECKLIST.md` (this file)

**Supporting Documents**:

- `DataForge/API.md` - API documentation
- `DataForge/ARCHITECTURE.md` - System architecture
- `PHASE_3_VERIFICATION_CHECKLIST.md` - Testing procedures

**Quick Commands**:

```bash
# Run all tests
cd DataForge && pytest tests/ -v --cov=app

# Run specific connector tests
pytest tests/test_github_connector.py -v
pytest tests/test_discord_connector.py -v
pytest tests/test_rfc_connector.py -v

# Manual API testing
curl -X POST http://localhost:8001/api/v1/search/external \
  -H "Content-Type: application/json" \
  -d '{"query": "OAuth2", "sources": ["github", "discord", "rfc"]}'

# Frontend testing
cd vibeforge && pnpm dev
```

---

## 📈 Progress Dashboard

```
PHASE 4 PROGRESS
================

Week 1: Core Connectors [############          ] 25%
├─ Day 1: GitHub        [ ✓ ] Ready
├─ Day 2: Discord       [   ] Not Started
├─ Day 3: RFC           [   ] Not Started
└─ Day 4: Integration   [   ] Not Started

Week 2: Testing         [                      ] 0%
├─ Day 5-6: Tests       [   ] Not Started
├─ Day 7-8: NeuroForge  [   ] Not Started
└─ Day 9: VibeForge     [   ] Not Started

Week 3: Frontend        [                      ] 0%
├─ Day 10-11: Filters   [   ] Not Started
├─ Day 12-13: Export    [   ] Not Started
└─ Day 14: Polish       [   ] Not Started

Overall: [##########                        ] 15%

Timeline: 2-4 weeks (Est: Dec 4-18)
Status: Ready to Begin ✅
```

---

**Ready to start Phase 4? Begin with Day 1 and the GitHub Connector Guide! 🚀**

**Next Action**: Create `DataForge/app/services/github_connector.py` and copy code from `GITHUB_CONNECTOR_GUIDE.md`
