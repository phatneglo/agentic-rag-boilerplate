"""
Database session management and initialization.
Handles async PostgreSQL connections and database setup.
"""

import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from sqlalchemy.ext.declarative import declarative_base
from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Create SQLAlchemy Base for future models
Base = declarative_base()

# Global variables for database engine and session factory
_engine = None
_async_session_factory = None


def get_database_url() -> str:
    """
    Get the database URL from settings.
    Falls back to the configured PostgreSQL URL if not set via environment.
    """
    if settings.database_url:
        return settings.database_url
    
    # Configured PostgreSQL URL with provided credentials
    configured_url = "postgresql+asyncpg://postgres:0yq5h3to9@localhost:5432/standard_eassist_chat"
    logger.info(f"Using configured database: standard_eassist_chat")
    return configured_url


def get_engine():
    """Get or create the async database engine."""
    global _engine
    
    if _engine is None:
        database_url = get_database_url()
        
        _engine = create_async_engine(
            database_url,
            echo=settings.debug,  # Log SQL queries in debug mode
            poolclass=NullPool,  # Disable connection pooling for simplicity
            future=True,
        )
        
        logger.info("Database engine created")
    
    return _engine


def get_session_factory():
    """Get or create the async session factory."""
    global _async_session_factory
    
    if _async_session_factory is None:
        engine = get_engine()
        _async_session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        logger.info("Database session factory created")
    
    return _async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    Use this in FastAPI endpoints and other async functions.
    """
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def init_db():
    """
    Initialize the database by creating all tables.
    Call this during application startup.
    """
    try:
        engine = get_engine()
        
        # Create all tables (currently none, but ready for future models)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Database tables created successfully")
        
        # Test the connection
        await test_connection()
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise


async def test_connection():
    """Test the database connection."""
    try:
        async with get_session_factory()() as session:
            # Execute a simple query to test connection
            result = await session.execute(text("SELECT 1"))
            result.fetchone()  # Don't await this
            
        logger.info("✅ Database connection test successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection test failed: {e}")
        return False


async def close_db():
    """
    Close database connections.
    Call this during application shutdown.
    """
    global _engine
    
    if _engine:
        await _engine.dispose()
        _engine = None
        logger.info("Database connections closed")


# Utility function for running database operations
async def run_db_operation(operation):
    """
    Run a database operation with proper session management.
    
    Args:
        operation: An async function that takes a session as argument
    
    Example:
        async def create_user(session, name):
            user = User(name=name)
            session.add(user)
            return user
        
        user = await run_db_operation(lambda session: create_user(session, "John"))
    """
    async with get_session_factory()() as session:
        try:
            result = await operation(session)
            await session.commit()
            return result
        except Exception as e:
            await session.rollback()
            logger.error(f"Database operation failed: {e}")
            raise 