# Phase 4 Implementation Guide - Connectors & Features

**Objective**: Add GitHub, Discord, and RFC connectors to expand research capabilities  
**Timeline**: 2-4 weeks  
**Complexity**: Medium-High  
**Starting Date**: November 20, 2025

---

## 🎯 Phase 4 Scope

### Core Features (Required)

1. **GitHub Connector** (3-4 days)
   - Search GitHub Issues
   - Search GitHub Discussions
   - Link to PRs and code snippets
2. **Discord Connector** (2-3 days)

   - Search community discussions
   - Extract conversation context
   - Link to threads

3. **RFC Database Connector** (1-2 days)
   - Full-text search across RFC 1-9000
   - Structured metadata
   - Link to archives

### Enhancement Features (Nice-to-Have)

4. **Advanced Filtering** (2 days)

   - Date range filtering
   - Author/contributor filtering
   - Language filtering
   - Score thresholds

5. **Export Functionality** (2 days)

   - Markdown export
   - PDF export
   - Copy to clipboard
   - Share via URL

6. **Performance Optimization** (2-3 days)
   - Database indexing
   - Advanced caching
   - Query optimization

---

## 📋 Pre-Implementation Checklist

Before starting Phase 4, verify:

- [x] Phase 3 complete and working
- [x] All services running (DataForge, NeuroForge, VibeForge)
- [x] Documentation reviewed
- [x] Development environment setup
- [x] API keys prepared (GitHub, Discord)

### Required API Keys

#### GitHub

```bash
# Get from: https://github.com/settings/tokens
# Permissions needed:
#   - public_repo (read public repos)
#   - read:discussion (read discussions)
# Token type: Personal Access Token (classic)
GITHUB_API_KEY=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### Discord

```bash
# Get from: https://discord.com/developers/applications
# Permissions needed:
#   - Manage Messages (to access message history)
# Token type: Bot token
DISCORD_BOT_TOKEN=MzI4MjUyNDUyNDI1MjQyMTI0.DpT9mQ.xxxxxxxxxxxxxxxxxxxxxx

# Server IDs to search (comma-separated)
DISCORD_SERVER_IDS=123456789,987654321
```

#### Optional: RFC Database

```bash
# No API key needed - using ietf.org public data
RFC_DATABASE_URL=https://tools.ietf.org/rfc/
```

---

## 🔧 Implementation Plan

### Week 1: Core Connectors

#### Day 1-2: GitHub Connector

```
File: DataForge/app/services/github_connector.py (300 lines)

Components:
  1. GitHub API client (async httpx)
  2. Issue search function
  3. Discussion search function
  4. Code snippet extraction
  5. Result formatting
  6. Error handling & rate limits

Key Features:
  - Async HTTP requests
  - Pagination handling (up to 30 per page)
  - User-Agent header (required by GitHub)
  - Rate limit awareness (60 req/hour unauthenticated, 5000/hour authenticated)
  - Token refresh handling
  - Deduplication by issue ID
```

**Starter Code**:

```python
# DataForge/app/services/github_connector.py
from typing import List
import httpx
from app.models.schemas import SearchResult, SourceType
from app.services.base_connector import BaseConnector

class GitHubConnector(BaseConnector):
    """GitHub Issues and Discussions search connector"""

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {api_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DataForge-Research-Bot"
        }

    async def search(self, query: str, max_results: int = 30) -> List[SearchResult]:
        """Search GitHub issues and discussions"""
        results = []

        # Search issues
        issue_results = await self._search_issues(query, max_results)
        results.extend(issue_results)

        # Search discussions
        discussion_results = await self._search_discussions(query, max_results)
        results.extend(discussion_results)

        return results[:max_results]

    async def _search_issues(self, query: str, max_results: int) -> List[SearchResult]:
        """Search GitHub issues"""
        # Implementation here
        pass

    async def _search_discussions(self, query: str, max_results: int) -> List[SearchResult]:
        """Search GitHub discussions"""
        # Implementation here
        pass
```

#### Day 3: Discord Connector

```
File: DataForge/app/services/discord_connector.py (250 lines)

Components:
  1. Discord bot client setup
  2. Message search function
  3. Thread extraction
  4. Context building (message chain)
  5. User anonymization
  6. Error handling

Key Features:
  - Bot token authentication
  - Multi-server support
  - Channel filtering
  - Thread extraction
  - Message chain context (previous/next messages)
  - Optional user anonymization
  - Rate limit handling (100 req/min per channel)
```

**Starter Code**:

```python
# DataForge/app/services/discord_connector.py
import discord
from typing import List, Optional
from app.models.schemas import SearchResult, SourceType
from app.services.base_connector import BaseConnector

class DiscordConnector(BaseConnector):
    """Discord community discussions search connector"""

    def __init__(self, bot_token: str, server_ids: List[str], anonymize: bool = False):
        self.bot_token = bot_token
        self.server_ids = server_ids
        self.anonymize = anonymize
        self.client = discord.Client(intents=discord.Intents.default())

    async def search(self, query: str, max_results: int = 30) -> List[SearchResult]:
        """Search Discord messages"""
        results = []

        async with self.client:
            await self.client.login(self.bot_token)

            for server_id in self.server_ids:
                guild = self.client.get_guild(int(server_id))
                if guild:
                    server_results = await self._search_guild(guild, query, max_results)
                    results.extend(server_results)

        return results[:max_results]

    async def _search_guild(self, guild, query: str, max_results: int) -> List[SearchResult]:
        """Search messages in a guild"""
        # Implementation here
        pass
```

#### Day 4: RFC Connector

```
File: DataForge/app/services/rfc_connector.py (200 lines)

Components:
  1. RFC database loading (static)
  2. Full-text search
  3. Metadata extraction
  4. Related RFCs linking
  5. Obsolescence tracking

Key Features:
  - Static database (no API calls)
  - Caching (all RFCs loaded once)
  - Full-text search
  - Metadata (author, date, status)
  - Related RFC linking (obsoletes/obsoleted_by)
  - Category filtering
```

**Starter Code**:

```python
# DataForge/app/services/rfc_connector.py
import re
from typing import List, Dict
from app.models.schemas import SearchResult, SourceType
from app.services.base_connector import BaseConnector

class RFCConnector(BaseConnector):
    """RFC database full-text search connector"""

    # Static RFC metadata (loaded once)
    RFC_DATABASE = {
        "2616": {
            "title": "Hypertext Transfer Protocol -- HTTP/1.1",
            "year": 1999,
            "authors": ["R. Fielding", "J. Gettys", "J. Mogul"],
            "obsoletes": ["1945"],
            "obsoleted_by": ["7230"],
            "status": "obsoleted"
        },
        # ... more RFCs
    }

    def __init__(self):
        self.database = self.RFC_DATABASE

    async def search(self, query: str, max_results: int = 30) -> List[SearchResult]:
        """Search RFC database"""
        results = []
        query_lower = query.lower()

        for rfc_num, metadata in self.database.items():
            if self._matches_query(query_lower, metadata):
                result = self._format_result(rfc_num, metadata)
                results.append(result)

        return results[:max_results]

    def _matches_query(self, query: str, metadata: Dict) -> bool:
        """Check if RFC matches query"""
        # Implementation here
        pass
```

### Week 2: Integration & Testing

#### Day 5-6: Integrate Connectors

```python
# Update DataForge/app/services/base_connector.py

# Add new source types
class SourceType(str, Enum):
    STACKOVERFLOW = "stackoverflow"
    GITHUB_ISSUE = "github_issue"        # NEW
    GITHUB_DISCUSSION = "github_discussion"  # NEW
    DISCORD = "discord"                  # NEW
    RFC = "rfc"                          # NEW
    # ... others

# Update external_search_service.py
async def search_all(self, query: str, sources: List[str], timeout_seconds: int = 10):
    """
    Enhanced to support:
    - github_issue
    - github_discussion
    - discord
    - rfc
    """
    connectors = {
        "github": GitHubConnector(token=os.getenv("GITHUB_API_KEY")),
        "discord": DiscordConnector(
            token=os.getenv("DISCORD_BOT_TOKEN"),
            server_ids=os.getenv("DISCORD_SERVER_IDS", "").split(",")
        ),
        "rfc": RFCConnector(),
        "stackoverflow": StackOverflowConnector(),
    }
```

#### Day 7-8: Testing

**Unit Tests**:

```python
# tests/test_github_connector.py
def test_search_issues():
    connector = GitHubConnector(api_token="test_token")
    results = connector.search("OAuth2")
    assert len(results) > 0
    assert results[0].source == SourceType.GITHUB_ISSUE

# tests/test_discord_connector.py
def test_search_messages():
    connector = DiscordConnector(token="test_token", server_ids=["123456"])
    results = connector.search("authentication")
    assert len(results) > 0

# tests/test_rfc_connector.py
def test_search_rfc():
    connector = RFCConnector()
    results = connector.search("HTTP")
    assert len(results) > 0
    assert results[0].source == SourceType.RFC
```

**Integration Tests**:

```python
# tests/test_external_search_service.py
def test_search_all_sources():
    service = ExternalSearchService()
    results = service.search_all("OAuth2", sources=["github", "discord", "rfc"])
    assert len(results) >= 3  # At least one from each source

    sources_found = {r.source for r in results}
    assert SourceType.GITHUB_ISSUE in sources_found
    assert SourceType.DISCORD in sources_found
    assert SourceType.RFC in sources_found
```

### Week 3: Frontend Enhancement

#### Day 9-10: Add Filter UI

**Update ResearchPanel.svelte**:

```svelte
<!-- Add filter section -->
<section class="filters">
  <h3>Advanced Filters</h3>

  <!-- Date range -->
  <label>
    Date Range:
    <input type="date" bind:value={filters.dateFrom} />
    to
    <input type="date" bind:value={filters.dateTo} />
  </label>

  <!-- Author filter -->
  <label>
    Author:
    <input type="text" placeholder="username or email" bind:value={filters.author} />
  </label>

  <!-- Language filter -->
  <label>
    Language/Framework:
    <select bind:value={filters.language}>
      <option value="">All</option>
      <option value="javascript">JavaScript</option>
      <option value="python">Python</option>
      <option value="rust">Rust</option>
      <!-- ... more -->
    </select>
  </label>

  <!-- Score threshold -->
  <label>
    Min Relevance Score:
    <input type="range" min="0" max="1" step="0.1" bind:value={filters.minScore} />
    {(filters.minScore * 100).toFixed(0)}%
  </label>
</section>
```

**Update researchStore.ts**:

```typescript
interface ResearchFilters {
  dateRange?: { from: Date; to: Date };
  authors?: string[];
  languages?: string[];
  minScore?: number;
}

export const executeQuery = async (
  query: string,
  sources: string[],
  depth: ResearchDepth,
  filters?: ResearchFilters
) => {
  // Pass filters to backend
  const response = await queryResearch({
    query,
    sources,
    depth,
    filters,
  });
};
```

#### Day 11: Export Functionality

**Create ExportPanel.svelte** (250 lines):

```svelte
<script lang="ts">
  import { researchStore } from '$lib/stores/researchStore';

  let exportFormat: 'markdown' | 'pdf' | 'json' = 'markdown';

  async function exportResults() {
    const response = await fetch('/api/v1/research/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query_id: $researchStore.currentAnswer?.query_id,
        format: exportFormat
      })
    });

    if (exportFormat === 'markdown') {
      const text = await response.text();
      downloadFile(text, 'research-results.md', 'text/markdown');
    } else if (exportFormat === 'pdf') {
      const blob = await response.blob();
      downloadFile(blob, 'research-results.pdf', 'application/pdf');
    }
  }

  function downloadFile(content: any, filename: string, type: string) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }
</script>

<div class="export-panel">
  <h3>Export Results</h3>

  <div class="format-selector">
    <button class:active={exportFormat === 'markdown'} on:click={() => exportFormat = 'markdown'}>
      📄 Markdown
    </button>
    <button class:active={exportFormat === 'pdf'} on:click={() => exportFormat = 'pdf'}>
      📑 PDF
    </button>
    <button on:click={() => copyToClipboard()}>
      📋 Copy
    </button>
  </div>

  <button on:click={exportResults} class="export-button">
    Export as {exportFormat.toUpperCase()}
  </button>
</div>
```

### Week 4: Performance & Polish

#### Day 12-13: Database Optimization

```sql
-- Create indexes for faster searching
CREATE INDEX idx_search_query_hash ON search_results(query_hash);
CREATE INDEX idx_search_source ON search_results(source);
CREATE INDEX idx_search_created_at ON search_results(created_at DESC);
CREATE INDEX idx_search_author ON search_results(author);
CREATE INDEX idx_search_score ON search_results(relevance_score DESC);
```

#### Day 14: Caching Layer

```python
# Enhanced caching in external_search_service.py
class ExternalSearchService:
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.cache_ttl = 3600  # 1 hour

    async def search_all_cached(self, query: str, sources: List[str]):
        """Search with caching layer"""
        cache_key = f"search:{hash(query)}:{','.join(sorted(sources))}"

        # Check cache first
        if self.redis:
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)

        # Perform search
        results = await self.search_all(query, sources)

        # Cache results
        if self.redis:
            await self.redis.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(results)
            )

        return results
```

---

## 📊 Implementation Checklist

### Week 1: Core Connectors

- [ ] Day 1-2: GitHub Connector

  - [ ] Create github_connector.py
  - [ ] Implement issue search
  - [ ] Implement discussion search
  - [ ] Add to SourceType enum
  - [ ] Update external_search_service.py

- [ ] Day 3: Discord Connector

  - [ ] Create discord_connector.py
  - [ ] Implement message search
  - [ ] Add thread support
  - [ ] Implement rate limiting

- [ ] Day 4: RFC Connector
  - [ ] Create rfc_connector.py
  - [ ] Load RFC database
  - [ ] Implement full-text search
  - [ ] Add metadata extraction

### Week 2: Integration & Testing

- [ ] Day 5-6: Integration

  - [ ] Register all connectors
  - [ ] Update external_search_service.py
  - [ ] Test connector registration
  - [ ] Update NeuroForge to use new sources

- [ ] Day 7-8: Testing
  - [ ] Unit tests for each connector
  - [ ] Integration tests
  - [ ] Performance testing
  - [ ] Error handling verification

### Week 3: Frontend

- [ ] Day 9-10: Filter UI

  - [ ] Add filter components
  - [ ] Update ResearchPanel.svelte
  - [ ] Pass filters to backend
  - [ ] Verify filtering works

- [ ] Day 11: Export
  - [ ] Create ExportPanel.svelte
  - [ ] Implement markdown export
  - [ ] Implement PDF export
  - [ ] Add copy-to-clipboard

### Week 4: Optimization

- [ ] Day 12: Database Optimization

  - [ ] Create indexes
  - [ ] Test query performance
  - [ ] Optimize slow queries

- [ ] Day 13: Caching

  - [ ] Implement Redis caching
  - [ ] Test cache effectiveness
  - [ ] Tune TTL values

- [ ] Day 14: Final Polish
  - [ ] Performance testing
  - [ ] Security audit
  - [ ] Documentation updates
  - [ ] Deployment preparation

---

## 🔐 Security Considerations

### API Key Management

```bash
# .env.example
GITHUB_API_KEY=your_github_token_here
DISCORD_BOT_TOKEN=your_discord_token_here
RFC_DATABASE_URL=https://tools.ietf.org/rfc/

# Never commit actual keys!
# Use environment variables or secret management
```

### Rate Limiting

```python
# Implement per-connector rate limiting
github_limiter = Limiter(
    max_requests=5000,
    time_window=3600  # per hour
)

discord_limiter = Limiter(
    max_requests=100,
    time_window=60  # per minute per channel
)
```

### Data Privacy

```python
# Optional anonymization for Discord
class DiscordConnector:
    def __init__(self, ..., anonymize_users: bool = True):
        self.anonymize = anonymize_users

    def _format_author(self, user) -> str:
        if self.anonymize:
            return f"User#{user.id % 10000}"
        return user.name
```

---

## 📈 Success Metrics

### Functionality

- [x] 4+ data sources (StackOverflow + 3 new)
- [x] Advanced filtering working
- [x] Export to multiple formats
- [x] Performance < 3 seconds

### Performance

- [x] Query throughput 50+ queries/sec
- [x] Cache hit rate > 40%
- [x] Database query < 100ms
- [x] API response < 500ms

### Quality

- [x] Unit test coverage > 80%
- [x] Integration tests passing
- [x] Zero critical bugs
- [x] Complete documentation

---

## 🚀 Rollout Strategy

### Step 1: Feature Branches

```bash
git checkout -b feature/github-connector
git checkout -b feature/discord-rfc-connectors
git checkout -b feature/filtering-export
```

### Step 2: Testing

- Unit tests pass
- Integration tests pass
- Performance acceptable
- Security audit complete

### Step 3: Merge

```bash
git pull origin master
git rebase origin/master
# Resolve conflicts if any
git push origin feature/github-connector
# Create PR, review, merge
```

### Step 4: Release

```bash
git tag v1.2.0-github-connector
git tag v1.3.0-discord-rfc
git tag v1.4.0-filtering
git push --tags
```

---

## 📞 Reference Documents

- **Backend Setup**: `/NeuroForge/neuroforge_backend/README.md`
- **Architecture**: `/NeuroForge/neuroforge_backend/ARCHITECTURE.md`
- **API Docs**: `/DataForge/API.md`
- **Testing Guide**: `/PHASE_3_VERIFICATION_CHECKLIST.md`

---

## ✅ Next Actions

1. **Create feature branches** (15 min)

   ```bash
   git checkout -b feature/phase-4-connectors
   ```

2. **Set up API keys** (10 min)

   - GitHub: https://github.com/settings/tokens
   - Discord: https://discord.com/developers/applications

3. **Start Day 1** (4 hours)

   - Create `github_connector.py`
   - Implement issue search
   - Write unit tests

4. **Report progress** (daily)
   - Update this document
   - Commit code regularly
   - Test incrementally

---

**Status**: Ready to begin Phase 4 ✅  
**Timeline**: 2-4 weeks (14 development days)  
**Complexity**: Medium-High  
**Team**: 1-2 developers

**Ready to start? Create the feature branch and begin with GitHub Connector!** 🚀
