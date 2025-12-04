"""
Test script to verify telemetry is working correctly.

Run this to ensure the telemetry system is set up properly.
"""

import sys
import os
import uuid
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from forge_telemetry import TelemetryClient
from app.database import DATABASE_URL
from sqlalchemy import create_engine, text


def test_telemetry_basic():
    """Test basic telemetry emission."""
    print("Test 1: Basic telemetry emission")
    print("-" * 40)

    telemetry = TelemetryClient(DATABASE_URL)

    # Emit a simple test event
    event_id = telemetry.emit(
        service="dataforge",
        event_type="test_event",
        severity="info",
        correlation_id=uuid.uuid4(),
        metadata={"test": "basic_emission"},
        metrics={"value": 123}
    )

    print(f"✅ Event emitted with ID: {event_id}")
    return True


def test_telemetry_with_metadata():
    """Test telemetry with complex metadata."""
    print("\nTest 2: Telemetry with complex metadata")
    print("-" * 40)

    telemetry = TelemetryClient(DATABASE_URL)

    event_id = telemetry.emit(
        service="dataforge",
        event_type="query",
        severity="info",
        correlation_id=uuid.uuid4(),
        metadata={
            "query": "test query",
            "user": "charles",
            "filters": ["type:article", "year:2024"],
            "nested": {"key": "value"}
        },
        metrics={
            "duration_ms": 45.6,
            "results_count": 10,
            "cache_hit": True
        }
    )

    print(f"✅ Event with complex data emitted: {event_id}")
    return True


def test_telemetry_error_handling():
    """Test telemetry error event."""
    print("\nTest 3: Error event emission")
    print("-" * 40)

    telemetry = TelemetryClient(DATABASE_URL)

    event_id = telemetry.emit(
        service="dataforge",
        event_type="query_error",
        severity="error",
        correlation_id=uuid.uuid4(),
        metadata={
            "error": "Database connection timeout",
            "error_type": "TimeoutError",
            "query": "failed query"
        },
        metrics={
            "duration_ms": 30000,
            "retry_count": 3
        }
    )

    print(f"✅ Error event emitted: {event_id}")
    return True


def verify_events_in_database():
    """Verify that events were written to the database."""
    print("\nTest 4: Verifying events in database")
    print("-" * 40)

    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Count events
        result = conn.execute(text("SELECT COUNT(*) as count FROM events"))
        count = result.fetchone()[0]
        print(f"✅ Found {count} events in database")

        # Get latest events
        result = conn.execute(text("""
            SELECT event_id, service, event_type, severity, timestamp
            FROM events
            ORDER BY timestamp DESC
            LIMIT 5
        """))

        print("\nLatest 5 events:")
        for row in result:
            print(f"  - {row[1]}/{row[2]} ({row[3]}) at {row[4]}")

    return count > 0


def test_correlation_id_tracing():
    """Test correlation ID for distributed tracing."""
    print("\nTest 5: Correlation ID tracing")
    print("-" * 40)

    telemetry = TelemetryClient(DATABASE_URL)
    correlation_id = uuid.uuid4()

    print(f"Using correlation_id: {correlation_id}")

    # Emit multiple events with same correlation_id
    telemetry.emit(
        service="dataforge",
        event_type="request_started",
        correlation_id=correlation_id,
        metadata={"endpoint": "/api/search"}
    )

    telemetry.emit(
        service="dataforge",
        event_type="query",
        correlation_id=correlation_id,
        metadata={"query": "test"},
        metrics={"duration_ms": 50}
    )

    telemetry.emit(
        service="dataforge",
        event_type="request_completed",
        correlation_id=correlation_id,
        metrics={"total_duration_ms": 100}
    )

    # Verify we can find all events by correlation_id
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) as count
            FROM events
            WHERE correlation_id = :correlation_id
        """), {"correlation_id": str(correlation_id)})

        count = result.fetchone()[0]
        print(f"✅ Found {count} events with correlation_id {correlation_id}")

    return count == 3


if __name__ == "__main__":
    print("=" * 60)
    print("Forge Telemetry Test Suite")
    print("=" * 60)

    tests = [
        test_telemetry_basic,
        test_telemetry_with_metadata,
        test_telemetry_error_handling,
        verify_events_in_database,
        test_correlation_id_tracing,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("\n🎉 All tests passed! Telemetry is working correctly.")
        print("\nNext steps:")
        print("1. Add telemetry to DataForge endpoints (see examples/telemetry_example.py)")
        print("2. Add telemetry to NeuroForge endpoints")
        print("3. Build Forge Command dashboard to visualize events")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        sys.exit(1)
