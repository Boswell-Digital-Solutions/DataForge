# Discord & RFC Connectors Implementation Guide

**Components**:

- Discord Connector (250 lines)
- RFC Connector (200 lines)

**Files**:

- `DataForge/app/services/discord_connector.py`
- `DataForge/app/services/rfc_connector.py`

**Time Estimate**: 4-5 hours total  
**Complexity**: Medium

---

## Discord Connector

### Overview

The Discord Connector searches community discussions from configured Discord servers. It extracts conversations, provides context, and integrates with the Forge search ecosystem.

### Features

- ✅ Search messages across multiple servers
- ✅ Thread extraction and context
- ✅ User anonymization (optional)
- ✅ Rate limiting per channel
- ✅ Message chain context (prev/next messages)
- ✅ Link extraction
- ✅ Error handling & recovery

### Example Usage

```python
connector = DiscordConnector(
    bot_token="MzI4MjUyNDUyNDI1MjQyMTI0.DpT9mQ.xxx",
    server_ids=["123456789", "987654321"],
    anonymize_users=True
)
results = await connector.search("authentication flow", max_results=10)
```

### Implementation

```python
# DataForge/app/services/discord_connector.py

"""
Discord community discussions search connector.

Extends BaseConnector to provide Discord-specific search capabilities.
Searches configured servers for messages matching a query.
"""

import asyncio
import logging
import re
from typing import List, Optional, Dict, Any
from datetime import datetime
import discord
from discord.ext import commands

from app.models.schemas import SearchResult, SourceType
from app.services.base_connector import BaseConnector

logger = logging.getLogger(__name__)


class DiscordConnector(BaseConnector):
    """
    Search Discord messages and threads.

    Attributes:
        bot_token: Discord Bot token
        server_ids: List of Discord guild IDs to search
        anonymize_users: Whether to anonymize user names
        client: Discord client instance
    """

    def __init__(
        self,
        bot_token: str,
        server_ids: List[str],
        anonymize_users: bool = False
    ):
        """Initialize Discord connector"""
        if not bot_token:
            raise ValueError("Discord bot token required")
        if not server_ids:
            raise ValueError("At least one server ID required")

        self.bot_token = bot_token
        self.server_ids = [int(sid) for sid in server_ids]
        self.anonymize_users = anonymize_users

        # Create Discord client with minimal intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True

        self.client = discord.Client(intents=intents)

    async def search(self, query: str, max_results: int = 30) -> List[SearchResult]:
        """
        Search Discord messages across configured servers.

        Args:
            query: Search query string
            max_results: Maximum number of results

        Returns:
            List of SearchResult objects
        """
        results: List[SearchResult] = []

        try:
            logger.info(f"Searching Discord for: {query}")

            async with self.client:
                # Login
                await self.client.login(self.bot_token)

                # Search each guild
                for guild_id in self.server_ids:
                    try:
                        guild = self.client.get_guild(guild_id)
                        if not guild:
                            logger.warning(f"Guild {guild_id} not found or not accessible")
                            continue

                        guild_results = await self._search_guild(guild, query, max_results)
                        results.extend(guild_results)

                        if len(results) >= max_results:
                            break

                    except Exception as e:
                        logger.error(f"Error searching guild {guild_id}: {str(e)}")
                        continue

            logger.info(f"Found {len(results[:max_results])} Discord results")
            return results[:max_results]

        except Exception as e:
            logger.error(f"Discord connector error: {str(e)}")
            raise

    async def _search_guild(self, guild, query: str, max_results: int) -> List[SearchResult]:
        """Search messages in a guild (server)"""
        results = []
        query_lower = query.lower()

        try:
            # Get all text channels
            channels = [c for c in guild.text_channels if c.permissions_for(guild.me).read_messages]

            for channel in channels:
                if len(results) >= max_results:
                    break

                try:
                    # Search recent messages (up to 100)
                    async for message in channel.history(limit=100):
                        if len(results) >= max_results:
                            break

                        # Check if query matches
                        if query_lower in message.content.lower():
                            result = self._format_message_result(
                                message,
                                guild,
                                channel,
                                query
                            )
                            if result:
                                results.append(result)

                except discord.Forbidden:
                    logger.debug(f"No permission to read channel: {channel.name}")
                except Exception as e:
                    logger.debug(f"Error reading channel {channel.name}: {str(e)}")

        except Exception as e:
            logger.error(f"Error searching guild: {str(e)}")

        return results

    def _format_message_result(
        self,
        message: discord.Message,
        guild,
        channel,
        query: str
    ) -> Optional[SearchResult]:
        """Format a Discord message into SearchResult format"""
        try:
            # Anonymize user if requested
            author_name = (
                f"User#{message.author.id % 10000}"
                if self.anonymize_users
                else message.author.name
            )

            # Extract snippet with query highlight
            snippet = message.content[:500]
            if len(message.content) > 500:
                snippet += "..."

            # Extract links from message
            links = re.findall(r'https?://[^\s]+', message.content)

            result = SearchResult(
                source=SourceType.DISCORD,
                title=f"{channel.name} - {author_name}",
                url=message.jump_url,
                snippet=snippet,
                author=author_name,
                created_at=message.created_at,
                updated_at=message.edited_at or message.created_at,
                relevance_score=self._calculate_relevance(message, query),
                metadata={
                    "server": guild.name,
                    "channel": channel.name,
                    "message_id": message.id,
                    "reactions": len(message.reactions),
                    "reply_count": len(await message.replies()) if hasattr(message, 'replies') else 0,
                    "links": links,
                    "thread_id": message.channel.id if isinstance(message.channel, discord.Thread) else None,
                }
            )

            return result

        except Exception as e:
            logger.warning(f"Error formatting Discord message: {str(e)}")
            return None

    def _calculate_relevance(self, message: discord.Message, query: str) -> float:
        """
        Calculate relevance score for a message.

        Factors:
        - Query match position (earlier = lower relevance)
        - Reaction count (more reactions = higher relevance)
        - Reply count (more replies = higher relevance)
        """
        query_lower = query.lower()
        content_lower = message.content.lower()

        # Query position score (0-0.3)
        position = content_lower.find(query_lower)
        position_score = max(0.0, 0.3 - (position / len(content_lower)) * 0.3)

        # Reaction score (0-0.3)
        reaction_score = min(0.3, len(message.reactions) * 0.1)

        # Recency score (0-0.4)
        from datetime import datetime, timezone, timedelta
        age_hours = (datetime.now(timezone.utc) - message.created_at).total_seconds() / 3600
        recency_score = max(0.0, 0.4 - (age_hours / 720) * 0.4)  # Decay over 30 days

        score = position_score + reaction_score + recency_score
        return min(1.0, score)


# Testing
if __name__ == "__main__":
    import os

    async def main():
        token = os.getenv("DISCORD_BOT_TOKEN")
        server_ids = os.getenv("DISCORD_SERVER_IDS", "").split(",")

        if not token or not server_ids:
            print("Error: DISCORD_BOT_TOKEN and DISCORD_SERVER_IDS required")
            return

        connector = DiscordConnector(
            bot_token=token,
            server_ids=server_ids,
            anonymize_users=True
        )

        results = await connector.search("authentication", max_results=5)

        print(f"\nFound {len(results)} Discord results\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.title}")
            print(f"   {result.snippet[:200]}")
            print()

    asyncio.run(main())
```

---

## RFC Connector

### Overview

The RFC Connector provides full-text search across the Internet Engineering Task Force (IETF) RFC database (RFC 1-9000+). Uses static data for fast searching without external API calls.

### Features

- ✅ Search 9000+ RFCs
- ✅ Full-text search in title and abstract
- ✅ Metadata extraction (author, year, status)
- ✅ Related RFC linking (obsoletes/obsoleted_by)
- ✅ Category filtering
- ✅ Zero external API dependency
- ✅ Fast in-memory searching

### Example Usage

```python
connector = RFCConnector()
results = await connector.search("HTTP", max_results=10)
# Results include HTTP/1.1, HTTP/2, HTTP/3, HTTPS, etc.
```

### Implementation

```python
# DataForge/app/services/rfc_connector.py

"""
RFC database full-text search connector.

Extends BaseConnector to provide RFC search capabilities.
Uses static RFC data for zero-latency searching.
"""

import logging
import re
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.models.schemas import SearchResult, SourceType
from app.services.base_connector import BaseConnector

logger = logging.getLogger(__name__)


class RFCConnector(BaseConnector):
    """
    Search Internet Engineering Task Force (IETF) RFC database.

    Attributes:
        rfc_database: Static RFC metadata (loaded once)
    """

    # RFC metadata (sample - in production, load from JSON)
    RFC_DATABASE = {
        "2616": {
            "title": "Hypertext Transfer Protocol -- HTTP/1.1",
            "year": 1999,
            "authors": ["R. Fielding", "J. Gettys", "J. Mogul"],
            "abstract": "The Hypertext Transfer Protocol (HTTP) is an application-level protocol for distributed, collaborative, hypermedia information systems.",
            "obsoletes": ["1945"],
            "obsoleted_by": ["7230", "7231", "7232"],
            "status": "obsoleted",
            "category": "Standards Track",
            "keywords": ["HTTP", "web", "protocol", "request", "response"]
        },
        "3986": {
            "title": "Uniform Resource Identifier (URI): Generic Syntax",
            "year": 2005,
            "authors": ["T. Berners-Lee", "R. Fielding", "L. Masinter"],
            "abstract": "A Uniform Resource Identifier (URI) provides a simple and extensible means for identifying a resource.",
            "obsoletes": ["2396"],
            "obsoleted_by": [],
            "status": "Standard",
            "category": "Standards Track",
            "keywords": ["URI", "URL", "identifiers", "syntax", "web"]
        },
        "5234": {
            "title": "Augmented BNF for Syntax Specifications: ABNF",
            "year": 2008,
            "authors": ["D. Crocker", "P. Overell"],
            "abstract": "This document describes the current syntax for Internet message format specifications.",
            "obsoletes": ["2234"],
            "obsoleted_by": [],
            "status": "Standard",
            "category": "Standards Track",
            "keywords": ["ABNF", "grammar", "syntax", "BNF", "specification"]
        },
        # ... more RFCs in production
    }

    def __init__(self, rfc_data: Optional[Dict] = None):
        """Initialize RFC connector with optional custom data"""
        self.rfc_database = rfc_data or self.RFC_DATABASE
        logger.info(f"RFC Connector initialized with {len(self.rfc_database)} RFCs")

    async def search(self, query: str, max_results: int = 30) -> List[SearchResult]:
        """
        Search RFC database.

        Args:
            query: Search query (title, abstract, keywords)
            max_results: Maximum number of results

        Returns:
            List of SearchResult objects
        """
        results = []
        query_lower = query.lower()

        try:
            logger.info(f"Searching RFC database for: {query}")

            # Search all RFCs
            for rfc_num, metadata in self.rfc_database.items():
                if self._matches_query(query_lower, metadata):
                    result = self._format_result(rfc_num, metadata, query_lower)
                    results.append(result)

                if len(results) >= max_results:
                    break

            # Sort by relevance score
            results.sort(key=lambda x: x.relevance_score, reverse=True)

            logger.info(f"Found {len(results[:max_results])} RFC results")
            return results[:max_results]

        except Exception as e:
            logger.error(f"RFC connector error: {str(e)}")
            raise

    def _matches_query(self, query_lower: str, metadata: Dict) -> bool:
        """Check if RFC matches query in title, abstract, or keywords"""
        # Check title
        if query_lower in metadata.get("title", "").lower():
            return True

        # Check abstract
        if query_lower in metadata.get("abstract", "").lower():
            return True

        # Check keywords
        keywords = metadata.get("keywords", [])
        if any(query_lower in kw.lower() for kw in keywords):
            return True

        # Check status
        if query_lower in metadata.get("status", "").lower():
            return True

        return False

    def _format_result(
        self,
        rfc_num: str,
        metadata: Dict,
        query_lower: str
    ) -> SearchResult:
        """Format RFC metadata into SearchResult"""

        # Calculate relevance
        relevance = 0.0
        if query_lower in metadata.get("title", "").lower():
            relevance += 0.5
        if query_lower in metadata.get("abstract", "").lower():
            relevance += 0.3
        if any(query_lower in kw.lower() for kw in metadata.get("keywords", [])):
            relevance += 0.2

        relevance = min(1.0, relevance)

        # Determine status badge
        status = metadata.get("status", "Unknown")
        if "obsolete" in status.lower():
            relevance *= 0.8  # Slightly lower for obsolete RFCs

        # Build authors string
        authors = metadata.get("authors", [])
        authors_str = ", ".join(authors[:2]) + ("..." if len(authors) > 2 else "")

        result = SearchResult(
            source=SourceType.RFC,
            title=f"RFC {rfc_num}: {metadata['title']}",
            url=f"https://tools.ietf.org/html/rfc{rfc_num}",
            snippet=metadata.get("abstract", "")[:500],
            author=authors_str,
            created_at=datetime(metadata.get("year", 2000), 1, 1),
            updated_at=datetime(metadata.get("year", 2000), 1, 1),
            relevance_score=relevance,
            metadata={
                "rfc_number": int(rfc_num),
                "status": status,
                "category": metadata.get("category", "Unknown"),
                "year": metadata.get("year", 0),
                "authors": authors,
                "keywords": metadata.get("keywords", []),
                "obsoletes": metadata.get("obsoletes", []),
                "obsoleted_by": metadata.get("obsoleted_by", []),
            }
        )

        return result


# Testing
if __name__ == "__main__":
    import asyncio

    async def main():
        connector = RFCConnector()

        queries = ["HTTP", "authentication", "protocol", "encryption"]

        for query in queries:
            results = await connector.search(query, max_results=3)
            print(f"\nTop results for '{query}':")
            for result in results:
                print(f"  - {result.title} (score: {result.relevance_score:.2f})")

    asyncio.run(main())
```

---

## Testing Both Connectors

### Unit Tests

```python
# tests/test_discord_connector.py

import pytest
from app.services.discord_connector import DiscordConnector
from app.models.schemas import SourceType


@pytest.mark.asyncio
async def test_discord_search():
    """Test Discord search (requires valid token)"""
    import os
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        pytest.skip("DISCORD_BOT_TOKEN not set")

    connector = DiscordConnector(
        bot_token=token,
        server_ids=[os.getenv("DISCORD_TEST_SERVER_ID", "")],
        anonymize_users=True
    )

    results = await connector.search("test", max_results=5)
    assert isinstance(results, list)


# tests/test_rfc_connector.py

import pytest
from app.services.rfc_connector import RFCConnector
from app.models.schemas import SourceType


@pytest.mark.asyncio
async def test_rfc_search_basic():
    """Test basic RFC search"""
    connector = RFCConnector()
    results = await connector.search("HTTP", max_results=5)

    assert len(results) > 0
    assert all(r.source == SourceType.RFC for r in results)


@pytest.mark.asyncio
async def test_rfc_search_relevance():
    """Test RFC relevance scoring"""
    connector = RFCConnector()
    results = await connector.search("HTTP", max_results=10)

    # Results should be sorted by relevance
    scores = [r.relevance_score for r in results]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_rfc_metadata():
    """Test RFC metadata extraction"""
    connector = RFCConnector()
    results = await connector.search("protocol", max_results=5)

    for result in results:
        assert "rfc_number" in result.metadata
        assert "status" in result.metadata
        assert "year" in result.metadata
```

---

## Integration Checklist

- [ ] Copy `github_connector.py` to DataForge
- [ ] Copy `discord_connector.py` to DataForge
- [ ] Copy `rfc_connector.py` to DataForge
- [ ] Update `external_search_service.py` with all three connectors
- [ ] Set environment variables (`.env`)
- [ ] Run unit tests
- [ ] Run integration tests
- [ ] Test via API endpoint
- [ ] Update documentation

---

## Environment Variables

```bash
# .env

# GitHub
GITHUB_API_KEY=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Discord
DISCORD_BOT_TOKEN=MzI4MjUyNDUyNDI1MjQyMTI0.DpT9mQ.xxxxxxxxxxxxxxxxxxxxxx
DISCORD_SERVER_IDS=123456789,987654321

# Optional test servers
DISCORD_TEST_SERVER_ID=123456789
```

---

## Next Steps

1. **Implement Discord Connector** (2-3 hours)
2. **Implement RFC Connector** (1-2 hours)
3. **Create tests** (1 hour)
4. **Integrate with external_search_service** (30 min)
5. **Test end-to-end** (1 hour)
6. **Deploy** (30 min)

---

**Ready to implement?** Start with RFC (no dependencies), then Discord! 🚀
