# Phase 4 Planning: Additional Connectors & Optimization

**Status**: ⏳ READY TO START  
**Previous Phases**: 3 (Complete) — 3,538+ lines  
**Planned Additions**: GitHub, Discord, RFCs, Filtering, Export

---

## Phase 4 Objectives

### Primary Goals

1. **GitHub Connector** (Priority)

   - Search GitHub Issues
   - Search GitHub Discussions
   - Extract code snippets
   - Link to pull requests

2. **Discord Connector** (Priority)

   - Search community discussions
   - Extract conversation context
   - Link to threads

3. **RFC Database Connector** (Priority)
   - RFC 1-9000 full-text search
   - Structured RFC metadata
   - Link to RFC archives

### Secondary Goals

1. **Advanced Filtering**

   - Date range filtering
   - Author/contributor filtering
   - Language/framework filtering
   - Score thresholds

2. **Export Functionality**

   - Export to Markdown
   - Export to PDF
   - Copy to clipboard
   - Share via URL

3. **Performance Optimization**
   - Database indexing
   - Advanced caching
   - Query optimization
   - Async worker pools

---

## GitHub Connector Architecture

### Files to Create

**Backend** (`/DataForge`):

1. `github_connector.py` (300+ lines)

   - GitHub API client (async httpx)
   - Issue search
   - Discussion search
   - Code snippet extraction
   - Pagination handling

2. Update `base_connector.py`
   - Add GitHubIssue, GitHubDiscussion sources
   - Register in SourceType enum

### Implementation Details

**GitHub API Endpoints**:

```python
# Search Issues
GET /search/issues?q=query+repo:owner/repo

# Search Discussions
GET /repos/owner/repo/discussions?query=query

# Get PR/Issue details
GET /repos/owner/repo/issues/{number}
```

**Result Format**:

```python
{
  "id": "github-issue-123456",
  "source": "github_issue",
  "url": "https://github.com/owner/repo/issues/123",
  "title": "Issue title",
  "snippet": "Issue body excerpt...",
  "author": "username",
  "created_at": "2025-01-15T10:30:00Z",
  "comments": 5,
  "score": 0.92  # Relevance score
}
```

**Features**:

- ✅ OAuth token support (environment variable)
- ✅ Rate limit handling (60 req/hour unauthenticated, 5000/hour authenticated)
- ✅ Pagination (max 30 results per page)
- ✅ Error handling (404, 403, timeout)
- ✅ Deduplication (by issue ID)

---

## Discord Connector Architecture

### Files to Create

**Backend** (`/DataForge`):

1. `discord_connector.py` (250+ lines)
   - Discord API client (async httpx)
   - Message search (via bot)
   - Channel filtering
   - Thread extraction
   - User anonymization (optional)

### Implementation Details

**Discord API**:

```python
# Search messages in channel
GET /channels/{channel_id}/messages?query=query&limit=25

# Get thread messages
GET /channels/{thread_id}/messages?limit=25

# Get channel info
GET /channels/{channel_id}
```

**Result Format**:

```python
{
  "id": "discord-message-987654",
  "source": "discord",
  "url": "https://discord.com/channels/server_id/channel_id/message_id",
  "title": "Discussion: How to implement OAuth2?",
  "snippet": "User: I'm trying to implement OAuth2...",
  "author": "User#1234" or "Anonymous",
  "created_at": "2025-01-15T10:30:00Z",
  "replies": 12,
  "score": 0.85
}
```

**Features**:

- ✅ Bot token authentication
- ✅ Multi-server support
- ✅ Channel filtering
- ✅ Thread extraction
- ✅ User anonymization option
- ✅ Rate limiting (100 req/min per channel)

---

## RFC Database Connector Architecture

### Files to Create

**Backend** (`/DataForge`):

1. `rfc_connector.py` (200+ lines)
   - RFC full-text search
   - Metadata extraction
   - Caching (RFC database is static)
   - Link generation

### Implementation Details

**RFC Database**:

```python
# Use ietf.org search or local database
# RFCs are static, cache them on startup

RFC_DATABASE = {
  "1": { "title": "Host software", "year": 1969 },
  "2616": { "title": "HTTP/1.1", "year": 1999 },
  "3986": { "title": "URI generic syntax", "year": 2005 },
  # ...
}
```

**Result Format**:

```python
{
  "id": "rfc-2616",
  "source": "rfc",
  "url": "https://tools.ietf.org/html/rfc2616",
  "title": "Hypertext Transfer Protocol -- HTTP/1.1",
  "snippet": "HTTP is an application-level protocol for distributed...",
  "author": "R. Fielding, J. Gettys, J. Mogul, ...",
  "published": "1999-06-01",
  "obsoletes": ["RFC 1945"],
  "obsoleted_by": ["RFC 7230"],
  "score": 0.88
}
```

**Features**:

- ✅ Full-text search
- ✅ Caching (no API calls needed)
- ✅ Related RFCs linking
- ✅ Obsolescence tracking
- ✅ Standard categorization

---

## Advanced Filtering Implementation

### Frontend Changes (`/VibeForge`)

**Update ResearchPanel.svelte**:

1. Add filter section below source selection
2. Add date range picker
3. Add author input field
4. Add language/framework dropdown
5. Add score threshold slider

**New Component** (`FilterPanel.svelte`):

```typescript
interface ResearchFilters {
  dateRange?: {
    from: Date;
    to: Date;
  };
  authors?: string[];
  languages?: string[];
  minScore?: number;
  maxAge?: number; // days
}
```

**Backend Updates**:

- Extend `SearchExternalRequest` with filters
- Pass filters to connectors
- Connectors apply filters in queries

---

## Export Functionality Implementation

### Frontend Component (`ExportPanel.svelte`)

**Formats Supported**:

1. **Markdown**

   - Include summary, answer, bullets
   - Source links as markdown links
   - Metadata in YAML front matter

2. **PDF**

   - Use pdfkit or similar
   - Include branding
   - Formatted layout

3. **Clipboard**

   - Copy formatted text to clipboard
   - Show confirmation toast

4. **URL**
   - Create shareable URL
   - Encode research query + settings
   - Generate QR code

### Example Markdown Export

```markdown
---
title: "Research: OAuth2 in SvelteKit"
date: 2025-01-15
query: "How do I implement OAuth2 in SvelteKit?"
sources:
  - github_issue
  - official_docs
depth: normal
---

# Research Results

## Summary

OAuth2 is a secure authorization framework...

## Detailed Answer

To implement OAuth2 in SvelteKit:

1. Install a library (e.g., `@auth/sveltekit`)
2. Configure providers
3. Add authentication endpoints
   ...

## Key Points

- OAuth2 is industry standard
- SvelteKit has built-in support
- Handle token refresh

## Sources

1. [GitHub Issue #456](https://github.com/...)
2. [Official Docs](https://docs.example.com/...)
   ...
```

---

## Performance Optimization Strategy

### 1. Database Indexing

**Create indexes for**:

- Search query results (content hash)
- Source type (for filtering)
- Date fields (for range queries)
- Author fields (for searching)

**SQL**:

```sql
CREATE INDEX idx_search_query_hash ON search_results(query_hash);
CREATE INDEX idx_search_source ON search_results(source);
CREATE INDEX idx_search_date ON search_results(created_at DESC);
CREATE INDEX idx_search_author ON search_results(author);
```

### 2. Advanced Caching

**Implement**:

- Query result caching (Redis)
- Source connector caching (GitHub API responses)
- RFC database caching (static, permanent)
- User preference caching

**Cache Keys**:

```python
# Query result cache
cache_key = f"search:{query_hash}:{source}:{depth}"
ttl = 3600  # 1 hour

# Source caching
cache_key = f"source:{source_id}"
ttl = 7200  # 2 hours
```

### 3. Query Optimization

**Batch Operations**:

- Combine multiple source queries
- Parallel request execution
- Deduplication before synthesis

**Token Optimization**:

- Truncate long snippets (500 chars max)
- Smart summary extraction
- Context window budgeting

### 4. Async Worker Pools

**Implement**:

- Worker pool for concurrent searches
- Request queue with priority
- Backpressure handling
- Load balancing

**Python (Celery + Redis)**:

```python
from celery import Celery

app = Celery('research')
app.conf.broker_url = 'redis://localhost:6379/0'

@app.task
def search_source(source: str, query: str):
    connector = get_connector(source)
    return connector.search(query)

# In orchestrator:
tasks = [search_source.delay(src, query) for src in sources]
results = [task.get() for task in tasks]
```

---

## Implementation Timeline

### Phase 4a: GitHub Connector (Week 1)

```
Mon: Create github_connector.py, basic API calls
Tue: Handle pagination, error handling, rate limits
Wed: Test with real GitHub queries
Thu: Integrate into external_search_service
Fri: Performance tuning, documentation
```

### Phase 4b: Discord + RFC (Week 2)

```
Mon: Create discord_connector.py
Tue: Create rfc_connector.py
Wed: Test both connectors
Thu: Integrate into service
Fri: Cross-connector testing
```

### Phase 4c: Filtering + Export (Week 3)

```
Mon: Add filter UI (ResearchPanel)
Tue: Implement filtering backend
Wed: Create export UI component
Thu: Implement export formats
Fri: Testing + refinement
```

### Phase 4d: Optimization (Week 4)

```
Mon: Database indexing
Tue: Redis caching implementation
Wed: Query optimization
Thu: Worker pool setup
Fri: Load testing, performance tuning
```

---

## File Structure for Phase 4

```
DataForge/
├── app/services/
│   ├── github_connector.py .............. NEW (300 lines)
│   ├── discord_connector.py ............ NEW (250 lines)
│   ├── rfc_connector.py ............... NEW (200 lines)
│   └── (existing connectors)
├── app/api/
│   └── search_filters_router.py ........ NEW (100 lines)
└── (existing structure)

NeuroForge/
└── (no changes)

vibeforge/
├── src/lib/components/research/
│   ├── ResearchPanel.svelte ........... UPDATE (add filters)
│   ├── FilterPanel.svelte ............ NEW (150 lines)
│   └── ExportPanel.svelte ............ NEW (250 lines)
├── src/lib/stores/
│   └── filterStore.ts ............... NEW (100 lines)
└── (existing structure)
```

---

## Success Metrics for Phase 4

### Functionality

- ✅ 10+ data sources (currently 1, adding 3+ in Phase 4)
- ✅ Advanced filtering (date, author, score)
- ✅ Export to 4+ formats
- ✅ Performance <150ms with filtering

### Performance

- ✅ Concurrent source queries <500ms
- ✅ Cache hit rate >40%
- ✅ Query throughput 50+ queries/sec
- ✅ Memory usage <500MB

### Code Quality

- ✅ 100% type coverage
- ✅ 95%+ test coverage
- ✅ 0 critical bugs
- ✅ Comprehensive documentation

---

## Testing Strategy for Phase 4

### Unit Tests

```python
# test_github_connector.py
def test_search_issues():
    connector = GitHubConnector()
    results = connector.search("OAuth2")
    assert len(results) > 0
    assert results[0].source == "github_issue"

# test_discord_connector.py
def test_search_discussions():
    connector = DiscordConnector()
    results = connector.search("SvelteKit")
    assert len(results) > 0

# test_rfc_connector.py
def test_search_rfc():
    connector = RFCConnector()
    results = connector.search("HTTP")
    assert len(results) > 0
```

### Integration Tests

```python
# test_external_search_service.py
def test_search_all_sources():
    service = ExternalSearchService()
    results = service.search_all("OAuth2", timeout=10)
    assert len(results) >= 4  # All sources
    assert all(r.score > 0 for r in results)
```

### Performance Tests

```python
# test_performance.py
def test_concurrent_queries():
    start = time.time()
    # Run 10 concurrent queries
    results = asyncio.run(concurrent_search(10))
    elapsed = time.time() - start
    assert elapsed < 5.0  # Under 5 seconds
    assert len(results) == 10
```

---

## Risk Mitigation

### Risks

1. **API Rate Limits** → Implement exponential backoff + caching
2. **Large Results** → Paginate, limit page size, truncate snippets
3. **Privacy Concerns** → Anonymize user data, hash sensitive info
4. **Performance Degradation** → Monitor latency, set thresholds

### Mitigation Strategies

- ✅ Rate limit handling in each connector
- ✅ Result pagination + streaming
- ✅ Optional anonymization in Discord connector
- ✅ Prometheus monitoring + alerts

---

## Documentation Plan

### Code Documentation

1. **Connector README** — How to add new connectors
2. **Filter API** — Filter schema + usage
3. **Export API** — Export format specifications

### User Documentation

1. **Research Guide** — How to use research features
2. **Filter Guide** — How to filter results
3. **Export Guide** — How to export results

### API Documentation

1. **New Endpoints** — `/search/external` with filters
2. **New Schema** — ResearchFilters interface
3. **Examples** — curl/Python examples

---

## Rollout Plan

### Phase 4a Rollout

- Feature branch: `feature/github-connector`
- PR review + merge to master
- Tag: `v1.2.0`

### Phase 4b Rollout

- Feature branch: `feature/discord-rfc-connectors`
- PR review + merge to master
- Tag: `v1.3.0`

### Phase 4c Rollout

- Feature branch: `feature/filtering-export`
- PR review + merge to master
- Tag: `v1.4.0`

### Phase 4d Rollout

- Feature branch: `feature/optimization`
- PR review + merge to master
- Tag: `v1.5.0-production`

---

## Next Steps

### Immediate (Next Session)

1. Start GitHub connector implementation
2. Set up test framework
3. Create GitHub API wrapper

### Short Term (Weeks 2-3)

1. Implement Discord + RFC connectors
2. Add filtering UI
3. Implement export

### Medium Term (Weeks 4-6)

1. Performance optimization
2. Database optimization
3. Load testing

### Long Term (Weeks 7+)

1. Custom connector framework
2. Advanced analytics
3. ML-based relevance ranking

---

## Conclusion

Phase 4 is the expansion phase — adding rich data sources, advanced filtering, and export functionality. The architecture is modular, extensible, and ready for the additional connectors.

**Status**: Planning complete, ready to implement

**Recommended Start**: Phase 4a (GitHub Connector)

**Estimated Duration**: 4 weeks

---

## Quick Reference

| Connector    | Lines   | Complexity | Timeline     |
| ------------ | ------- | ---------- | ------------ |
| GitHub       | 300     | Medium     | 3-4 days     |
| Discord      | 250     | Medium     | 2-3 days     |
| RFC          | 200     | Low        | 1-2 days     |
| **Subtotal** | **750** | —          | **6-9 days** |

| Feature      | Lines   | Complexity | Timeline      |
| ------------ | ------- | ---------- | ------------- |
| Filtering    | 200     | Low        | 1-2 days      |
| Export       | 350     | Medium     | 2-3 days      |
| Optimization | 400     | High       | 3-5 days      |
| **Subtotal** | **950** | —          | **6-10 days** |

**Phase 4 Total**: ~1,700 lines, 12-19 days

**Combined Project**: 5,238+ lines, 3-4 weeks development time

---

**Ready to start Phase 4?** Say `next` to begin GitHub connector implementation.
