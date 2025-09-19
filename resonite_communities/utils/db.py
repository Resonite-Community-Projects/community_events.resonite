from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from resonite_communities.utils.config import ConfigManager

config_manager = ConfigManager()

engine = create_async_engine(
    config_manager.infrastructure_config.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://'),
    echo=False,
    pool_size=config_manager.infrastructure_config.DB_POOL_SIZE,
    max_overflow=config_manager.infrastructure_config.DB_MAX_OVERFLOW,
    pool_timeout=config_manager.infrastructure_config.DB_POOL_TIMEOUT,
    pool_recycle=config_manager.infrastructure_config.DB_POOL_RECYCLE,
    pool_pre_ping=config_manager.infrastructure_config.DB_POOL_PRE_PING,
)

async_session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

from sqlalchemy.ext.asyncio import AsyncSession
from resonite_communities.utils.logger import get_logger


from contextvars import ContextVar
from contextlib import asynccontextmanager


_async_session_context: ContextVar[AsyncSession] = ContextVar('async_session')


async def get_current_async_session() -> AsyncSession:
    """Get the current async context session, or create a new one if needed"""
    try:
        session = _async_session_context.get()
        if session is None:
            session = async_session_maker()
            _async_session_context.set(session)
        return session
    except LookupError:
        session = async_session_maker()
        _async_session_context.set(session)
        return session

def set_async_session_context(session: AsyncSession):
    """Set the session for current async context"""
    _async_session_context.set(session)

@asynccontextmanager
async def get_async_session():
    """Async context manager for database sessions"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            pass

@asynccontextmanager
async def async_request_session():
    """Context manager for request-scoped async sessions"""
    async with async_session_maker() as session:
        set_async_session_context(session)
        try:
            yield session
        finally:
            try:
                _async_session_context.set(None)
            except:
                pass

async def get_session_dependency():
    """FastAPI dependency function that yields database sessions"""
    async with async_session_maker() as session:
        yield session