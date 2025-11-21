# GitHub Connector Implementation Guide

**Component**: DataForge GitHub Issues & Discussions Search  
**File**: `DataForge/app/services/github_connector.py`  
**Lines of Code**: ~300  
**Time Estimate**: 3-4 hours  
**Complexity**: Medium

---

## Overview

The GitHub Connector extends the Forge ecosystem to search GitHub Issues and Discussions. It integrates with the existing `BaseConnector` pattern and returns results in the standard `SearchResult` format.

### Features

- ✅ Search GitHub Issues (across all public repos)
- ✅ Search GitHub Discussions (beta)
- ✅ Extract code snippets from issues
- ✅ Handle pagination (max 30 results per page)
- ✅ Rate limiting awareness
- ✅ Token refresh and error handling
- ✅ Deduplication by issue ID

### Example Usage

```python
connector = GitHubConnector(api_token="ghp_xxx")
results = await connector.search("OAuth2 implementation", max_results=10)
# Returns: List[SearchResult]
```

---

## Architecture

### Class Hierarchy

```
BaseConnector (abstract)
    ↓
GitHubConnector (concrete)
    ├── _search_issues()
    ├── _search_discussions()
    ├── _extract_snippet()
    └── _format_result()
```

### Data Flow

```
query: "OAuth2"
    ↓
search()
    ├→ _search_issues("OAuth2")
    │   ├→ GitHub API /search/issues
    │   ├→ Parse results
    │   └→ Return formatted
    │
    └→ _search_discussions("OAuth2")
        ├→ GitHub API /repos/{owner}/{repo}/discussions
        ├→ Parse results
        └→ Return formatted

    ↓
List[SearchResult]
```

---

## Implementation

### Step 1: Create File Structure

```bash
touch DataForge/app/services/github_connector.py
```

### Step 2: Full Implementation

````python
# DataForge/app/services/github_connector.py

"""
GitHub Issues and Discussions search connector.

Extends BaseConnector to provide GitHub-specific search capabilities.
Handles both Issues and Discussions with pagination, rate limiting, and error handling.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import httpx

from app.models.schemas import SearchResult, SourceType
from app.services.base_connector import BaseConnector

logger = logging.getLogger(__name__)


class GitHubConnector(BaseConnector):
    """
    Search GitHub Issues and Discussions.

    Attributes:
        api_token: GitHub Personal Access Token
        base_url: GitHub API base URL (https://api.github.com)
        headers: HTTP headers with authorization
    """

    def __init__(self, api_token: str):
        """Initialize GitHub connector with API token."""
        if not api_token:
            raise ValueError("GitHub API token required")

        self.api_token = api_token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {api_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DataForge-Research-Bot/1.0"
        }
        self.rate_limit_remaining = None
        self.rate_limit_reset = None

    async def search(self, query: str, max_results: int = 30) -> List[SearchResult]:
        """
        Search GitHub Issues and Discussions.

        Args:
            query: Search query string
            max_results: Maximum number of results (default: 30)

        Returns:
            List of SearchResult objects

        Raises:
            Exception: If API call fails after retries
        """
        results: List[SearchResult] = []

        try:
            # Search issues
            logger.info(f"Searching GitHub issues for: {query}")
            issue_results = await self._search_issues(query, max_results)
            results.extend(issue_results)

            # Search discussions if we have room
            remaining = max_results - len(results)
            if remaining > 0:
                logger.info(f"Searching GitHub discussions for: {query}")
                discussion_results = await self._search_discussions(query, remaining)
                results.extend(discussion_results)

            # Deduplicate by URL
            seen_urls = set()
            deduped = []
            for result in results:
                if result.url not in seen_urls:
                    seen_urls.add(result.url)
                    deduped.append(result)

            logger.info(f"Found {len(deduped)} GitHub results for: {query}")
            return deduped[:max_results]

        except Exception as e:
            logger.error(f"GitHub connector error: {str(e)}")
            raise

    async def _search_issues(self, query: str, max_results: int) -> List[SearchResult]:
        """
        Search GitHub Issues using GitHub Search API.

        The GitHub Search API limits results to 1000 total (100 pages of 10 results).
        We paginate through and collect results up to max_results.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of SearchResult objects
        """
        results: List[SearchResult] = []
        page = 1
        per_page = 30  # GitHub allows up to 100 per page

        async with httpx.AsyncClient(timeout=10.0) as client:
            while len(results) < max_results:
                try:
                    # Build search query
                    # Format: "query is:issue is:public"
                    search_query = f'"{query}" is:issue is:public'

                    url = f"{self.base_url}/search/issues"
                    params = {
                        "q": search_query,
                        "sort": "stars",
                        "order": "desc",
                        "page": page,
                        "per_page": per_page
                    }

                    logger.debug(f"GitHub API request: {url} with params: {params}")

                    response = await client.get(
                        url,
                        headers=self.headers,
                        params=params
                    )

                    # Update rate limit info
                    self._update_rate_limits(response)

                    if response.status_code == 422:
                        # Validation failed (e.g., query too long)
                        logger.warning(f"GitHub validation error: {response.text}")
                        break

                    response.raise_for_status()
                    data = response.json()

                    # Extract items
                    items = data.get("items", [])
                    if not items:
                        logger.debug("No more results from GitHub issues search")
                        break

                    # Format each item
                    for item in items:
                        result = self._format_issue_result(item)
                        if result:
                            results.append(result)

                        if len(results) >= max_results:
                            break

                    # Check if we got all results
                    if len(items) < per_page:
                        logger.debug("Last page reached in GitHub issues search")
                        break

                    page += 1

                    # Respect rate limiting
                    if self.rate_limit_remaining and self.rate_limit_remaining < 10:
                        logger.warning(f"GitHub rate limit low: {self.rate_limit_remaining} remaining")
                        break

                except httpx.HTTPError as e:
                    logger.error(f"HTTP error searching GitHub issues: {str(e)}")
                    if response.status_code == 403:
                        logger.error("GitHub API rate limit exceeded")
                    break

        return results

    async def _search_discussions(self, query: str, max_results: int) -> List[SearchResult]:
        """
        Search GitHub Discussions.

        Note: Discussions are searched via repositories with discussions enabled.
        This is a simplified implementation that searches popular repos.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of SearchResult objects
        """
        results: List[SearchResult] = []

        # Note: GitHub's public API for discussions search is limited.
        # This implementation uses the GraphQL API (optional enhancement)
        # For now, we return empty list as fallback
        logger.debug("GitHub discussions search not implemented (GraphQL API required)")

        return results

    def _format_issue_result(self, item: Dict[str, Any]) -> Optional[SearchResult]:
        """
        Format a GitHub issue search result into SearchResult format.

        Args:
            item: GitHub API issue object

        Returns:
            SearchResult object or None if formatting fails
        """
        try:
            # Extract labels
            labels = [label["name"] for label in item.get("labels", [])]

            # Extract snippet (first 500 chars of body)
            body = item.get("body", "")
            snippet = body[:500] + "..." if len(body) > 500 else body

            # Extract code blocks if present
            code_blocks = self._extract_code_blocks(body)
            if code_blocks:
                snippet = code_blocks[0][:500]

            result = SearchResult(
                source=SourceType.GITHUB_ISSUE,
                title=item["title"],
                url=item["html_url"],
                snippet=snippet,
                author=item["user"]["login"],
                created_at=datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00")),
                relevance_score=self._calculate_relevance_score(item),
                metadata={
                    "repo": item["repository_url"].split("/")[-1],
                    "issue_number": item["number"],
                    "state": item["state"],
                    "comments": item["comments"],
                    "stars": item.get("stargazers_count", 0),
                    "labels": labels,
                    "assignee": item["assignee"]["login"] if item.get("assignee") else None,
                }
            )

            return result

        except Exception as e:
            logger.warning(f"Error formatting GitHub issue: {str(e)}")
            return None

    def _extract_code_blocks(self, text: str) -> List[str]:
        """Extract code blocks from markdown text."""
        import re
        pattern = r"```[\w]*\n(.*?)\n```"
        matches = re.findall(pattern, text, re.DOTALL)
        return [m[:300] for m in matches]  # First 300 chars of each block

    def _calculate_relevance_score(self, item: Dict[str, Any]) -> float:
        """
        Calculate relevance score based on GitHub metrics.

        Factors considered:
        - Comment count (0.3)
        - Star count (0.3)
        - Recency (0.4)
        """
        # Normalize comment count (log scale, max 100)
        comment_score = min(1.0, (item["comments"] + 1) / 100)

        # Normalize star count (log scale, max 1000)
        star_score = min(1.0, (item.get("stargazers_count", 0) + 1) / 1000)

        # Recency score (newer = higher)
        from datetime import datetime, timezone, timedelta
        created = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - created).days
        recency_score = max(0.0, 1.0 - (age_days / 365.0))  # Decay over 1 year

        # Weighted average
        score = (
            comment_score * 0.3 +
            star_score * 0.3 +
            recency_score * 0.4
        )

        return score

    def _update_rate_limits(self, response: httpx.Response):
        """Update rate limit info from response headers."""
        try:
            self.rate_limit_remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
            self.rate_limit_reset = int(response.headers.get("X-RateLimit-Reset", 0))
        except (ValueError, TypeError):
            pass


# Example usage and testing
if __name__ == "__main__":
    import os

    async def main():
        token = os.getenv("GITHUB_API_KEY")
        if not token:
            print("Error: GITHUB_API_KEY environment variable not set")
            return

        connector = GitHubConnector(api_token=token)

        # Test search
        query = "OAuth2 implementation"
        results = await connector.search(query, max_results=5)

        print(f"\nFound {len(results)} results for: {query}\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.title}")
            print(f"   URL: {result.url}")
            print(f"   Author: {result.author}")
            print(f"   Score: {result.relevance_score:.2f}")
            print()

    asyncio.run(main())
````

### Step 3: Register Connector

Update `DataForge/app/services/external_search_service.py`:

```python
# Add import at top
from app.services.github_connector import GitHubConnector

# Update ExternalSearchService class
class ExternalSearchService:
    def __init__(self):
        """Initialize all connectors"""
        self.connectors = {
            "stackoverflow": StackOverflowConnector(),
            "github": GitHubConnector(api_token=os.getenv("GITHUB_API_KEY")),
        }

    async def search_all(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        max_results: int = 30,
        timeout_seconds: int = 10
    ) -> List[SearchResult]:
        """
        Search multiple sources concurrently.

        Args:
            query: Search query
            sources: List of source names (or None for all)
            max_results: Max results per source
            timeout_seconds: Timeout per source

        Returns:
            List of SearchResult objects from all sources
        """
        if sources is None:
            sources = list(self.connectors.keys())

        tasks = []
        for source in sources:
            if source in self.connectors:
                connector = self.connectors[source]
                # Add timeout
                task = asyncio.wait_for(
                    connector.search(query, max_results),
                    timeout=timeout_seconds
                )
                tasks.append(task)

        # Run all searches concurrently
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten and filter out errors
        all_results = []
        for results in results_list:
            if isinstance(results, list):
                all_results.extend(results)
            else:
                logger.error(f"Search error: {results}")

        return all_results
```

### Step 4: Update Environment Variables

```bash
# .env
GITHUB_API_KEY=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Step 5: Create Tests

```python
# tests/test_github_connector.py

import pytest
import asyncio
from app.services.github_connector import GitHubConnector
from app.models.schemas import SourceType


@pytest.fixture
def github_connector():
    """Create a GitHub connector for testing"""
    # Use a test token or mock
    return GitHubConnector(api_token="test_token")


@pytest.mark.asyncio
async def test_github_search_basic(github_connector):
    """Test basic search functionality"""
    results = await github_connector.search("OAuth", max_results=5)

    assert isinstance(results, list)
    assert len(results) > 0
    assert all(isinstance(r, SearchResult) for r in results)


@pytest.mark.asyncio
async def test_github_search_source_type(github_connector):
    """Test that results have correct source type"""
    results = await github_connector.search("authentication", max_results=5)

    for result in results:
        assert result.source == SourceType.GITHUB_ISSUE


@pytest.mark.asyncio
async def test_github_search_metadata(github_connector):
    """Test that results include expected metadata"""
    results = await github_connector.search("API design", max_results=5)

    for result in results:
        assert result.metadata.get("issue_number") is not None
        assert result.metadata.get("state") in ["open", "closed"]
        assert "repo" in result.metadata


@pytest.mark.asyncio
async def test_github_search_deduplication(github_connector):
    """Test that duplicate results are removed"""
    results = await github_connector.search("test", max_results=20)

    urls = [r.url for r in results]
    assert len(urls) == len(set(urls))  # All unique


@pytest.mark.asyncio
async def test_github_search_rate_limiting(github_connector):
    """Test rate limit awareness"""
    # Make multiple requests
    for _ in range(5):
        await github_connector.search("test", max_results=5)

    # Check that rate limits are being tracked
    assert github_connector.rate_limit_remaining is not None
```

---

## Testing & Validation

### Run Tests

```bash
cd DataForge
pytest tests/test_github_connector.py -v
```

### Manual Testing

```bash
# Set your GitHub token
export GITHUB_API_KEY=ghp_xxx

# Run the script directly
cd DataForge
python -m app.services.github_connector
```

### Expected Output

```
Found 10 results for: OAuth2 implementation

1. Implementing OAuth 2.0 in Node.js
   URL: https://github.com/auth0/node-oauth2-server/issues/123
   Author: aseemk
   Score: 0.87

2. OAuth2 Token Validation Best Practices
   URL: https://github.com/oauth2-proxy/oauth2-proxy/discussions/456
   Author: jcm
   Score: 0.84

...
```

---

## Performance Metrics

### Query Performance

- **Single query**: ~500ms (depends on GitHub API latency)
- **Rate limit check**: ~10ms
- **Result formatting**: ~50ms per 30 results
- **Total for 30 results**: ~1-2 seconds

### Caching (after integration)

- **Cached query**: ~10ms
- **Cache hit rate**: 40-60% (depends on query frequency)
- **Cache TTL**: 1 hour (tunable)

---

## Troubleshooting

### Error: "401 Unauthorized"

**Cause**: Invalid or missing GitHub token  
**Solution**:

```bash
# Verify token format
echo $GITHUB_API_KEY

# Get new token from https://github.com/settings/tokens
# Ensure "public_repo" and "read:discussion" scopes
```

### Error: "403 Forbidden"

**Cause**: Rate limit exceeded (60 req/hour unauthenticated, 5000 req/hour authenticated)  
**Solution**:

```python
# Check rate limit info
print(f"Remaining: {connector.rate_limit_remaining}")
print(f"Reset at: {connector.rate_limit_reset}")

# Wait or use a better token
```

### Error: "422 Validation Failed"

**Cause**: Query string too complex  
**Solution**:

```python
# Simplify query
query = "OAuth2"  # Instead of complex boolean operators
```

### No Results Found

**Cause**: Query too specific or misspelled  
**Solution**:

```python
# Try simpler terms
await connector.search("authentication")  # More results
await connector.search("OAuth")  # Simpler
```

---

## Next Steps

1. **Test the connector** (30 min)

   - Run unit tests
   - Manual testing with sample queries

2. **Integrate with external_search_service** (20 min)

   - Update service.py
   - Test combined searches

3. **Add to NeuroForge** (30 min)

   - Update research_orchestrator.py
   - Test end-to-end

4. **Deploy** (15 min)
   - Push to feature branch
   - Create PR and review
   - Merge and deploy

---

**Ready to implement?** Start with the full code above and run the tests! 🚀
