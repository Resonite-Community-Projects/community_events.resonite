import contextlib
from typing import Optional

from pydantic import BaseModel, ConfigDict
from fastapi import Depends


from resonite_communities.auth.users import optional_current_active_user, User
from resonite_communities.utils.db import get_current_async_session
from resonite_communities.auth.db import DiscordAccount

class DiscordAccountData(BaseModel):
    id: int
    name: str
    avatar_url: str
    user_communities: list[str]
    discord_update_retry_after: int

class UserAuthModel(BaseModel):
    discord_account: DiscordAccountData | None = None
    is_superuser: bool | None = False
    is_moderator: bool | None = False

    model_config = ConfigDict(arbitrary_types_allowed=True)

async def get_user_auth(user: User = Depends(optional_current_active_user)) -> Optional[UserAuthModel]:

    if not user:
        return

    user_auth_model = UserAuthModel(is_superuser=user.is_superuser, is_moderator=user.is_moderator)

    session = await get_current_async_session()
    for user_oauth_account in user.oauth_accounts:
        if user_oauth_account.oauth_name == "discord":
            discord_account_db = await session.get(DiscordAccount, user_oauth_account.discord_account_id)
            if discord_account_db:
                user_auth_model.discord_account = DiscordAccountData(
                    id=discord_account_db.id,
                    name=discord_account_db.name,
                    avatar_url=discord_account_db.avatar_url,
                    user_communities=discord_account_db.user_communities,
                    discord_update_retry_after=discord_account_db.discord_update_retry_after
                )

    return user_auth_model
