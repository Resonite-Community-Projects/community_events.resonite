from collections.abc import AsyncGenerator
import uuid

from fastapi import Depends
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase, SQLAlchemyBaseOAuthAccountTableUUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, relationship
from sqlalchemy import Column, ForeignKey, UUID, String, JSON
from fastapi_users_db_sqlalchemy.access_token import (
    SQLAlchemyAccessTokenDatabase,
    SQLAlchemyBaseAccessTokenTableUUID,
)

DATABASE_URL = "sqlite+aiosqlite:///./my_database.db"


class Base(DeclarativeBase):
    pass


class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
    __tablename__ = 'oauth_account'
    discord_account_id = Column(UUID, ForeignKey('discord_account.id'), unique=True, nullable=True)
    discord_account = relationship('DiscordAccount', back_populates='oauth_account', uselist=False)

class DiscordAccount(Base):
    __tablename__ = 'discord_account'
    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
    name: Mapped[str] = Column(String)
    avatar_url: Mapped[str] = Column(String)
    accessible_communities_events: Mapped[list[str]] = Column(JSON)
    oauth_account = relationship('OAuthAccount', back_populates='discord_account', uselist=False)


class User(SQLAlchemyBaseUserTableUUID, Base):
    oauth_accounts: Mapped[list[OAuthAccount]] = relationship(
        "OAuthAccount", lazy="joined"
    )

class AccessToken(SQLAlchemyBaseAccessTokenTableUUID, Base):
    pass


engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User, OAuthAccount)

async def get_access_token_db(
    session: AsyncSession = Depends(get_async_session),
):
    yield SQLAlchemyAccessTokenDatabase(session, AccessToken)