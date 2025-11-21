# Phase 4 Day 3 Quick Start Guide

**Date**: November 21, 2025  
**Status**: Ready to begin Day 3 - RFC Connector  
**Time Estimate**: 2-3 hours

---

## One-Line Summary

Implement RFC connector following the same architecture as GitHub and Discord connectors (completed Days 1-2).

---

## Quick Start

### 1. Review Pattern (5 min)

```bash
# Look at completed connectors
cat DataForge/app/connectors/github_connector.py | head -100
cat DataForge/app/connectors/discord_connector.py | head -100

# Review the base class
cat DataForge/app/connectors/base_connector.py | grep -A 20 "class BaseConnector"
```

### 2. RFC Connector Structure (Same as Discord/GitHub)

```python
class RFCConnector(BaseConnector):
    def __init__(self, *args):
        super().__init__(*args)

    async def search(query, max_results, filters):
        # 1. Query RFC database
        # 2. Format results to ConnectorResult
        # 3. Deduplicate by URL
        # 4. Return list

    async def validate_credentials(self):
        # No auth required - public API
        # Just check connectivity

    def _get_source_type(self):
        return SourceType.RFC
```

### 3. Create RFC Connector

**Target**: `DataForge/app/connectors/rfc_connector.py`  
**Size**: ~200 lines  
**Time**: ~30-45 min

**Key Methods**:

- `search(query, max_results, filters)` - Main entry
- `_search_rfc(query)` - Query RFC API
- `_format_rfc_result(rfc_item)` - Convert to ConnectorResult
- `_calculate_relevance_score(content, query)` - Scoring

**RFC API**: `https://www.rfc-editor.org/rfc/`

- Search: Query text/number
- Format: JSON available via API
- No auth needed
- Example: `https://www.rfc-editor.org/rfc/rfc5322.json`

### 4. Create RFC Tests

**Target**: `DataForge/tests/test_rfc_connector.py`  
**Size**: ~250 lines  
**Time**: ~45-60 min  
**Test Count**: 8-10 tests

**Test Categories** (follow GitHub/Discord pattern):

```
TestRFCConnectorBasic (3 tests)
  - test_connector_initialization
  - test_connector_no_base_url (optional)
  - test_source_type

TestRFCConnectorSearch (3 tests)
  - test_search_basic
  - test_search_deduplication
  - test_search_max_results

TestRFCConnectorFormatting (2 tests)
  - test_format_rfc_result
  - test_relevance_score_calculation

TestRFCConnectorErrorHandling (2 tests)
  - test_search_not_found
  - test_search_http_error

TestRFCConnectorValidation (1 test)
  - test_validate_connectivity
```

### 5. Run Tests

```bash
cd DataForge
python3 -m pytest tests/test_rfc_connector.py -v --tb=short

# Expected: 8-10 tests, 100% pass rate
```

### 6. Register in Service

**File**: `DataForge/app/services/external_search_service.py`

**Add**:

```python
from app.connectors.rfc_connector import RFCConnector

# In __init__:
self._connectors: Dict[SourceType, BaseConnector] = {
    SourceType.STACKOVERFLOW: StackOverflowConnector(),
    SourceType.GITHUB: GitHubConnector(),
    SourceType.DISCORD: DiscordConnector(...),
    SourceType.RFC: RFCConnector(),  # NEW
}
```

### 7. Commit

```bash
git add DataForge/app/connectors/rfc_connector.py
git add DataForge/tests/test_rfc_connector.py
git add DataForge/app/services/external_search_service.py
git commit -m "feat: implement RFC connector for Phase 4 - Day 3

- Create rfc_connector.py with RFC database search
- Support RFC number and title search
- Implement relevance scoring
- Add comprehensive unit tests (9 tests, all passing)
- Register connector in external_search_service.py
- ~200 lines of production code
- Full async/await support"
```

### 8. Verify All Tests Still Pass

```bash
python3 -m pytest tests/test_github_connector.py tests/test_discord_connector.py tests/test_rfc_connector.py -v

# Expected: 31 + 9 = 40 tests, 100% pass rate
```

---

## API Reference

### GitHub Connector (Reference)

```
Base: https://api.github.com
Search: GET /search/issues?q={query}
Result: Issues with details
Limit: 30 results
Auth: Token
```

### Discord Connector (Reference)

```
Base: https://discord.com/api/v10
Search: Guild channels → fetch messages
Result: Messages with embeds
Limit: 50 per channel
Auth: Bot token
```

### RFC Connector (To Implement)

```
Base: https://www.rfc-editor.org
Search: RFC number or title
Result: RFC metadata + content
Limit: No limit
Auth: None (public)
Format: JSON API available
Example URL: https://www.rfc-editor.org/rfc/rfc5322.json
```

---

## Code Template

### Basic Structure

```python
"""RFC Connector for Phase 4."""

import logging
from typing import List, Optional, Dict, Any
import httpx
from app.connectors.base_connector import BaseConnector, SourceType, ConnectorResult
from datetime import datetime

logger = logging.getLogger(__name__)

class RFCConnector(BaseConnector):
    """Search RFC documents."""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.rfc-editor.org"

    async def search(
        self,
        query: str,
        max_results: int = 30,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[ConnectorResult]:
        """Search RFC documents."""
        results = []

        try:
            logger.info(f"Searching RFC for: {query}")

            # 1. Query RFC API
            rfc_items = await self._search_rfc(query, max_results)

            # 2. Format results
            for item in rfc_items:
                result = self._format_rfc_result(item, query)
                if result and result.score > 0:
                    results.append(result)

            # 3. Deduplicate
            seen_urls = set()
            deduped = []
            for result in results:
                if result.url not in seen_urls:
                    seen_urls.add(result.url)
                    deduped.append(result)

            logger.info(f"Found {len(deduped)} RFC results for: {query}")
            return deduped[:max_results]

        except Exception as e:
            logger.error(f"RFC search error: {str(e)}")
            return []

    async def _search_rfc(self, query: str, max_results: int) -> List[Dict]:
        """Query RFC API."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Query logic here
            pass

    def _format_rfc_result(self, item: Dict, query: str) -> Optional[ConnectorResult]:
        """Format RFC item to ConnectorResult."""
        try:
            score = self._calculate_relevance_score(item.get("title", ""), query)
            return ConnectorResult(
                id=item.get("rfc_number"),
                url=f"{self.base_url}/rfc/rfc{item.get('rfc_number')}.html",
                title=item.get("title", "Unknown"),
                snippet=item.get("abstract", "")[:500],
                source=SourceType.RFC,
                score=score,
                indexed_at=datetime.utcnow().isoformat() + "Z",
                tags=[],
                metadata={
                    "rfc_number": item.get("rfc_number"),
                    "status": item.get("status"),
                }
            )
        except Exception as e:
            logger.error(f"Error formatting RFC result: {e}")
            return None

    def _calculate_relevance_score(self, content: str, query: str) -> float:
        """Calculate relevance score."""
        if not query or not content:
            return 0.0

        query_lower = query.lower()
        content_lower = content.lower()

        # Simple scoring
        if query_lower in content_lower:
            return 0.8
        return 0.3

    async def validate_credentials(self) -> bool:
        """Validate RFC API connectivity."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/rfc/rfc1.json")
                return response.status_code == 200
        except Exception:
            return False

    def _get_source_type(self) -> SourceType:
        return SourceType.RFC
```

---

## Testing Template

```python
"""Tests for RFC Connector."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.connectors.rfc_connector import RFCConnector
from app.connectors.base_connector import SourceType

@pytest.fixture
def rfc_connector():
    return RFCConnector()

class TestRFCConnectorBasic:
    def test_connector_initialization(self, rfc_connector):
        assert rfc_connector.base_url == "https://www.rfc-editor.org"
        assert rfc_connector.source_type == SourceType.RFC

    def test_source_type(self, rfc_connector):
        assert rfc_connector._get_source_type() == SourceType.RFC

class TestRFCConnectorSearch:
    @pytest.mark.asyncio
    async def test_search_basic(self, rfc_connector):
        # Mock HTTP response
        # Test search works
        pass

    @pytest.mark.asyncio
    async def test_search_deduplication(self, rfc_connector):
        # Test duplicates removed
        pass

# ... Continue with other test classes
```

---

## Progress Tracking

### Day 3 Checklist

- [ ] Create `rfc_connector.py` (200 lines)
- [ ] Create `test_rfc_connector.py` (250 lines)
- [ ] Run tests - verify 9/9 passing
- [ ] Register in ExternalSearchService
- [ ] All tests passing (40/40)
- [ ] Commit to feature branch
- [ ] Create Day 3 completion doc

### After Day 3

- [ ] All 3 connectors (GitHub, Discord, RFC)
- [ ] 40/40 tests passing
- [ ] Ready for Week 2 integration testing
- [ ] ~750 lines additional code

---

## Useful Commands

```bash
# Run just RFC tests
python3 -m pytest tests/test_rfc_connector.py -v

# Run all connector tests
python3 -m pytest tests/test_*_connector.py -v

# Show git branch status
git status

# View feature branch commits
git log feature/phase-4-connectors --oneline

# Check test coverage
python3 -m pytest tests/test_rfc_connector.py --cov=app.connectors.rfc_connector
```

---

## Success Criteria

✅ Complete when:

1. RFC connector implemented (~200 lines)
2. 8-10 tests written and passing
3. Registered in ExternalSearchService
4. 40/40 total tests passing (GitHub + Discord + RFC)
5. Committed to feature branch
6. Documentation complete

---

## Time Breakdown (2-3 hours total)

- Implementation: 45-60 min
- Testing: 45-60 min
- Registration & Integration: 15 min
- Testing verification: 15 min
- Commit & docs: 15 min
- **Buffer**: 15 min

---

## Key Points

✅ Follow GitHub/Discord pattern exactly  
✅ Use public RFC API (no auth)  
✅ Target 8-10 tests (like Day 1-2)  
✅ Deduplicate by URL  
✅ Graceful error handling  
✅ Comprehensive logging  
✅ Register in external_search_service.py  
✅ Keep async/await consistent

---

**Ready to start Day 3?** Run the first command above to review the patterns! 🚀
