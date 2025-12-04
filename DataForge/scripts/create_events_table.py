"""
Create the events table for telemetry directly in the database.

This script creates the telemetry events table without using migrations.
Run this if you're having migration issues.
"""

import sys
import os

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.database import DATABASE_URL


def create_events_table():
    """Create the events table for telemetry."""
    engine = create_engine(DATABASE_URL)

    # For SQLite, we use TEXT for UUID fields
    # For PostgreSQL, we would use UUID type
    is_sqlite = "sqlite" in DATABASE_URL.lower()

    if is_sqlite:
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            service VARCHAR(50) NOT NULL,
            event_type VARCHAR(100) NOT NULL,
            severity VARCHAR(20) NOT NULL,
            correlation_id TEXT,
            metadata TEXT,
            metrics TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    else:
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS events (
            event_id UUID PRIMARY KEY,
            timestamp TIMESTAMPTZ NOT NULL,
            service VARCHAR(50) NOT NULL,
            event_type VARCHAR(100) NOT NULL,
            severity VARCHAR(20) NOT NULL,
            correlation_id UUID,
            metadata JSONB,
            metrics JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """

    create_indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_events_service ON events(service);",
        "CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);",
        "CREATE INDEX IF NOT EXISTS idx_events_correlation_id ON events(correlation_id);",
        "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);",
    ]

    with engine.begin() as conn:
        print(f"Creating events table in {DATABASE_URL}...")
        conn.execute(text(create_table_sql))
        print("✓ Events table created")

        print("Creating indexes...")
        for idx_sql in create_indexes_sql:
            conn.execute(text(idx_sql))
        print("✓ Indexes created")

    print("\nTelemetry events table is ready!")
    print("You can now use forge-telemetry to emit events.")


if __name__ == "__main__":
    create_events_table()
