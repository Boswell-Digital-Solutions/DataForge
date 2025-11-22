"""
NeuroForge Database Module

Database initialization and session management.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


# Simple in-memory setup for MVP
engine = None
async_session_maker = None


async def init_db():
    """Initialize database connection."""
    global engine, async_session_maker
    # For MVP, we're using in-memory storage in workbench modules
    # This stub satisfies imports from main.py
    pass


async def close_db():
    """Close database connection."""
    global engine
    if engine:
        await engine.dispose()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    # Stub for MVP - workbench uses in-memory storage
    yield None
