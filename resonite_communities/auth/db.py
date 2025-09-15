from collections.abc import AsyncGenerator
import uuid

from fastapi import Depends
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase, SQLAlchemyBaseOAuthAccountTableUUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, relationship
from sqlalchemy import Column, ForeignKey, UUID, String, JSON, Integer, Boolean
from fastapi_users_db_sqlalchemy.access_token import (
    SQLAlchemyAccessTokenDatabase,
    SQLAlchemyBaseAccessTokenTableUUID,
)

from sqlalchemy.ext.asyncio import AsyncSession

from resonite_communities.utils.db import get_async_session, get_session_dependency

class BaseModel(DeclarativeBase):
    pass


class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, BaseModel):
    __tablename__ = 'oauth_account'
    discord_account_id = Column(Integer, ForeignKey('discord_account.id'), unique=True, nullable=True)
    discord_account = relationship('DiscordAccount', back_populates='oauth_account', uselist=False)

class DiscordAccount(BaseModel):
    __tablename__ = 'discord_account'
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    name: Mapped[str] = Column(String)
    avatar_url: Mapped[str] = Column(String)
    user_communities: Mapped[list[str]] = Column(JSON)
    discord_update_retry_after: Mapped[list[int]] = Column(Integer)
    oauth_account = relationship('OAuthAccount', back_populates='discord_account', uselist=False)


class User(SQLAlchemyBaseUserTableUUID, BaseModel):
    oauth_accounts: Mapped[list[OAuthAccount]] = relationship(
        "OAuthAccount", lazy="joined"
    )
    is_moderator: Mapped[bool] = Column(Boolean)
    is_protected: Mapped[bool] = Column(Boolean)

class AccessToken(SQLAlchemyBaseAccessTokenTableUUID, BaseModel):
    pass

async def get_user_db(session: AsyncSession = Depends(get_session_dependency)):
    yield SQLAlchemyUserDatabase(session, User, OAuthAccount)

async def get_access_token_db(
    session: AsyncSession = Depends(get_session_dependency),
):
    yield SQLAlchemyAccessTokenDatabase(session, AccessToken)
