import contextlib
from typing import Optional

from pydantic import BaseModel, ConfigDict
from fastapi import Depends


from resonite_communities.auth.users import current_active_user, User
from resonite_communities.auth.db import get_async_session, DiscordAccount

class UserAuthModel(BaseModel):
    discord_account: DiscordAccount

    model_config = ConfigDict(arbitrary_types_allowed=True)

async def get_user_auth(user: User = Depends(current_active_user)) -> Optional[UserAuthModel]:
    if not user.is_superuser:
        return None

    get_async_session_context = contextlib.asynccontextmanager(get_async_session)

    async with get_async_session_context() as session:
        for user_oauth_account in user.oauth_accounts:
            if user_oauth_account.oauth_name == "discord":
                discord_account = await session.get(DiscordAccount, user_oauth_account.discord_account_id)
                discord_account.is_superuser = user.is_superuser
                return UserAuthModel(discord_account=discord_account)
    return None