import contextlib
from typing import Optional

from pydantic import BaseModel, ConfigDict
from fastapi import Depends


from resonite_communities.auth.users import optional_current_active_user, User
from resonite_communities.utils.db import get_current_async_session
from resonite_communities.auth.db import DiscordAccount

class UserAuthModel(BaseModel):
    discord_account: DiscordAccount | None = None
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
            user_auth_model.discord_account = await session.get(DiscordAccount, user_oauth_account.discord_account_id)

    return user_auth_model