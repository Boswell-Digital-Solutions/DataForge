"""
Example demonstrating telemetry integration in DataForge.

This shows how to emit telemetry events for search queries.
"""

import sys
import os
import time
import uuid
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from forge_telemetry import TelemetryClient
from app.database import DATABASE_URL


def example_search_with_telemetry(query: str):
    """
    Example function showing how to add telemetry to a search operation.

    This demonstrates the pattern to use in real DataForge endpoints.
    """
    # Initialize telemetry client
    telemetry = TelemetryClient(DATABASE_URL)

    # Generate correlation ID for request tracing
    correlation_id = uuid.uuid4()
    start_time = time.time()

    print(f"\n🔍 Performing search: '{query}'")
    print(f"📊 Correlation ID: {correlation_id}")

    try:
        # Simulate search operation
        time.sleep(0.1)  # Simulate query time
        results = [
            {"id": 1, "title": "Result 1"},
            {"id": 2, "title": "Result 2"},
        ]

        # Calculate metrics
        duration_ms = (time.time() - start_time) * 1000

        # Emit SUCCESS event
        event_id = telemetry.emit(
            service="dataforge",
            event_type="query",
            severity="info",
            correlation_id=correlation_id,
            metadata={
                "query": query,
                "user": "charles",
                "endpoint": "/api/v1/search",
            },
            metrics={
                "duration_ms": duration_ms,
                "results_count": len(results),
                "cache_hit": False,
            }
        )

        print(f"✅ Search completed in {duration_ms:.2f}ms")
        print(f"📤 Telemetry event emitted: {event_id}")
        print(f"📈 Results: {len(results)} documents found")

        return results

    except Exception as e:
        # Calculate metrics even on error
        duration_ms = (time.time() - start_time) * 1000

        # Emit ERROR event
        event_id = telemetry.emit(
            service="dataforge",
            event_type="query_error",
            severity="error",
            correlation_id=correlation_id,
            metadata={
                "query": query,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            metrics={
                "duration_ms": duration_ms,
            }
        )

        print(f"❌ Search failed: {e}")
        print(f"📤 Error telemetry event emitted: {event_id}")

        raise


def example_ingestion_with_telemetry(documents: list):
    """
    Example function showing how to add telemetry to an ingestion operation.
    """
    telemetry = TelemetryClient(DATABASE_URL)
    correlation_id = uuid.uuid4()
    start_time = time.time()

    print(f"\n📥 Ingesting {len(documents)} documents")
    print(f"📊 Correlation ID: {correlation_id}")

    try:
        # Simulate ingestion
        time.sleep(0.2)
        total_chunks = len(documents) * 5  # Simulate chunking

        duration_ms = (time.time() - start_time) * 1000

        # Emit SUCCESS event
        event_id = telemetry.emit(
            service="dataforge",
            event_type="ingestion",
            severity="info",
            correlation_id=correlation_id,
            metadata={
                "source": "manual_upload",
                "user": "charles",
            },
            metrics={
                "duration_ms": duration_ms,
                "documents_count": len(documents),
                "chunks_created": total_chunks,
                "embeddings_generated": total_chunks,
            }
        )

        print(f"✅ Ingestion completed in {duration_ms:.2f}ms")
        print(f"📤 Telemetry event emitted: {event_id}")
        print(f"📦 Created {total_chunks} chunks from {len(documents)} documents")

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000

        event_id = telemetry.emit(
            service="dataforge",
            event_type="ingestion_error",
            severity="error",
            correlation_id=correlation_id,
            metadata={
                "error": str(e),
                "documents_count": len(documents),
            },
            metrics={
                "duration_ms": duration_ms,
            }
        )

        print(f"❌ Ingestion failed: {e}")
        print(f"📤 Error telemetry event emitted: {event_id}")

        raise


if __name__ == "__main__":
    print("=" * 60)
    print("DataForge Telemetry Example")
    print("=" * 60)

    # Example 1: Search query
    example_search_with_telemetry("machine learning papers")

    # Example 2: Document ingestion
    example_ingestion_with_telemetry([
        {"title": "Doc 1", "content": "..."},
        {"title": "Doc 2", "content": "..."},
        {"title": "Doc 3", "content": "..."},
    ])

    print("\n" + "=" * 60)
    print("✨ Telemetry examples completed successfully!")
    print("=" * 60)
    print("\nTo view events, query the 'events' table:")
    print("  SELECT * FROM events ORDER BY timestamp DESC LIMIT 10;")
